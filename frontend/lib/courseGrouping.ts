import { Course } from '@/lib/api';

export const getTermKeyFromDate = (dateString: string) => {
  const date = new Date(dateString);
  const year = date.getFullYear();
  const term = date.getMonth() < 6 ? 1 : 2;
  return `${year}/${term}`;
};

export const getCourseTermKey = (course: Course) =>
  course.term_year && course.term_number
    ? `${course.term_year}/${course.term_number}`
    : getTermKeyFromDate(course.created_at);

export const filterVisibleCourses = (
  courses: Course[],
  hiddenCourseIds: number[],
  hiddenTermKeys: string[],
  courseTab: 'classes' | 'hidden'
) =>
  courses.filter((course) => {
    const termKey = getCourseTermKey(course);
    if (courseTab === 'hidden') {
      return hiddenCourseIds.includes(course.id) || hiddenTermKeys.includes(termKey);
    }

    return !hiddenCourseIds.includes(course.id) && !hiddenTermKeys.includes(termKey);
  });

export const groupCoursesBySemester = (courses: Course[]) =>
  courses.reduce<Record<string, Course[]>>((acc, course) => {
    const key = getCourseTermKey(course);
    acc[key] = acc[key] || [];
    acc[key].push(course);
    return acc;
  }, {});

export const sortSemesterKeys = (semesterGroups: Record<string, Course[]>) =>
  Object.keys(semesterGroups).sort((a, b) => {
    const [yearA, termA] = a.split('/').map(Number);
    const [yearB, termB] = b.split('/').map(Number);
    if (yearA !== yearB) return yearB - yearA;
    return termB - termA;
  });
