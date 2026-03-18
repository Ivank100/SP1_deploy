from fastapi import APIRouter, HTTPException, status

from ...ingestion.audio import chunk_transcript_segments, transcribe_audio
from ...db.postgres import (
    clear_chunks_for_lecture,
    get_lecture,
    get_lecture_transcript,
    insert_chunks,
    save_lecture_transcript,
    update_lecture_status,
)
from ...services.embeddings import embed_texts
from ...ingestion.indexer import MAX_CHUNKS_FOR_V0
from ..models import TranscriptResponse, TranscriptSegment, TranscriptionResponse

router = APIRouter(prefix="/api/lectures", tags=["audio"])


def _ensure_audio_lecture(lecture_id: int):
    lecture = get_lecture(lecture_id)
    if not lecture:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lecture with id {lecture_id} not found",
        )
    if lecture[7] != "audio":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Transcription is only available for audio lectures",
        )
    return lecture


def _embed_and_store_audio_chunks(lecture_id: int, chunks_payload):
    texts = [chunk.get("text", "") for chunk in chunks_payload]
    embeddings = embed_texts(texts)
    clear_chunks_for_lecture(lecture_id)
    insert_chunks(lecture_id, chunks_payload, embeddings)


@router.post("/{lecture_id}/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio_lecture(lecture_id: int):
    """Trigger (re)transcription for an audio lecture."""
    lecture = _ensure_audio_lecture(lecture_id)
    file_path = lecture[2]

    try:
        update_lecture_status(lecture_id, "transcribing")
        transcript = transcribe_audio(file_path)
        chunks = chunk_transcript_segments(transcript)
        if len(chunks) > MAX_CHUNKS_FOR_V0:
            chunks = chunks[:MAX_CHUNKS_FOR_V0]

        _embed_and_store_audio_chunks(lecture_id, chunks)
        save_lecture_transcript(lecture_id, transcript)
        update_lecture_status(lecture_id, "completed")
    except HTTPException:
        # bubble up explicit HTTP errors
        raise
    except Exception as exc:  # noqa: BLE001
        update_lecture_status(lecture_id, "failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to transcribe audio: {exc}",
        ) from exc

    return TranscriptionResponse(
        lecture_id=lecture_id,
        status="completed",
        segment_count=len(chunks),
        message="Transcription completed successfully",
    )


@router.get("/{lecture_id}/transcript", response_model=TranscriptResponse)
async def get_audio_transcript(lecture_id: int):
    """Return stored transcript segments for a lecture."""
    lecture = get_lecture(lecture_id)
    if not lecture:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lecture with id {lecture_id} not found",
        )

    transcript = get_lecture_transcript(lecture_id)
    if transcript is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transcript not available for this lecture",
        )

    segments_payload = transcript.get("segments") or []
    segments = [
        TranscriptSegment(
            start=float(segment.get("start", 0.0)),
            end=float(segment.get("end", segment.get("start", 0.0))),
            text=(segment.get("text") or "").strip(),
        )
        for segment in segments_payload
        if (segment.get("text") or "").strip()
    ]

    if not segments:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transcript segments are empty",
        )

    return TranscriptResponse(
        lecture_id=lecture_id,
        segments=segments,
        language=transcript.get("language"),
        model=transcript.get("model"),
    )

