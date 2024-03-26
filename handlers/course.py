from typing import List
from fastapi import Depends
from sqlalchemy.future import select
from sqlalchemy import insert, update, delete, and_
from sqlalchemy.orm import selectinload


from exceptions import CourseNotFoundException
from authentication.permissions import CoursePermission


import schemas.course as course_schemas
from models.course import Course, CourseDivisions
from models.division import Division
from models.enrollment import Enrollment



class CourseHandler:

    def __init__(self, permission_class: CoursePermission = Depends(CoursePermission)) -> None:
        self.user = permission_class.user
        self.db = permission_class.db
        self.permission_class = permission_class
        self.NotFoundException = CourseNotFoundException()
        self.model = Course
        self.retrieve_query = (
            select(self.model).
            options(
                selectinload(self.model.divisions).
                options(
                    selectinload(Division.regulation),
                    selectinload(Division.department_1),
                    selectinload(Division.department_2),
                )
            )
        )
        if not self.user.is_admin:
            self.retrieve_query = self.retrieve_query.where(
                self.model.id.in_(
                    select(CourseDivisions.columns.course_id).
                    where(
                        CourseDivisions.columns.division_id.in_(
                            select(Division.id).
                            where(Division.users.any(id=self.user.id))
                        )
                    )
                )
            )


    async def get_all(self, regulation_id: int | None):
        courses = await self.db.execute(
            self.retrieve_query
            if not regulation_id else
            self.retrieve_query.where(
                self.model.id.in_(
                    select(CourseDivisions.columns.course_id).
                    where(
                        CourseDivisions.columns.division_id.in_(
                            select(Division.id).
                            where(Division.regulation_id==regulation_id)
                        )
                    )
                )
            )
        )
        return courses.scalars().all()


    async def create(self, course: course_schemas.CourseCreate):
        new_course = self.model(**course.dict(exclude={"divisions"}))
        self.db.add(new_course)
        if course.divisions:
            for d in course.divisions:
                division = await self.db.get(Division, d)
                new_course.divisions.append(division)
        await self.db.commit()
        await self.db.refresh(new_course)
        return await self.get_one(new_course.id)


    async def get_one(self, id: int):
        await self.permission_class.check_permission(id)
        query = self.retrieve_query.where(self.model.id == id)
        course = await self.db.execute(query)
        course = course.scalar()
        if course:
            return course
        raise self.NotFoundException


    async def get_by_code_and_division_or_none(self, code: str, division_id: int):
        #   try to get by code and division
        query = await self.db.execute(
            select(self.model).
            where(
                and_(
                    self.model.code == code,
                    self.model.divisions.any(id=division_id)
                )
            )
        )
        course = query.scalar()
        #   if not exists try to get by code only
        if not course:
            query = await self.db.execute(select(self.model).where(self.model.code == code))
            course = query.scalars().first()    
        #   return if exists
        if course:
            #   check if user has the access rights
            await self.permission_class.check_permission(course.id)
            return course
    

    async def check_required_and_not_passed(self, division_id: int, passed_enrollments: List[Enrollment]):
        passed_courses_query = await self.db.execute(
			select(Course.id).
			where(
				Course.id.in_([e.course_id for e in passed_enrollments])
			)
		)
        passed_courses = passed_courses_query.scalars().all()
        required_courses = await self.db.execute(
			select(Course).
			where(
				and_(
					Course.required==True,
					Course.divisions.any(id=division_id)
				)
			).
			except_(Course.id.in_(passed_courses)).
            exists()
		)
        return required_courses


    async def update(self, id: int, course: course_schemas.CourseCreate):
        existing_course = await self.get_one(id)
        for key, value in course.dict(exclude={"divisions"}).items():
                setattr(existing_course, key, value)
        if course.divisions is not None:
            existing_course.divisions.clear()
            for division_id in course.divisions:
                division = await self.db.get(Division, division_id)
                if division:
                    existing_course.divisions.append(division)
        await self.db.commit()
        await self.db.refresh(existing_course)
        return existing_course


    async def delete(self, id: int):
        await self.get_one(id)
        await self.db.execute(
            delete(self.model).
            where(self.model.id == id)
        )
        await self.db.commit()
        return