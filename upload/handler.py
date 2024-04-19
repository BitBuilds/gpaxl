from threading import Thread
import asyncio

from fastapi import UploadFile


from sqlalchemy.ext.asyncio import AsyncSession


from division.models import Division
from course.models import Course

from . import xl_handler

from department.handler import DepartmentHandler
from division.handler import DivisionHandler
from student.handler import StudentHandler
from course.handler import CourseHandler
from enrollment.handler import EnrollmentHandler
from regulation.models import Regulation
from user.models import User



class UploadHandler:


	def __init__(self, user: User, db: AsyncSession, file: UploadFile) -> None:
		self.file = file
		self.user = user
		self.db = db
		self.department_handler = DepartmentHandler(user, db)
		self.division_handler = DivisionHandler(user, db)
		self.student_handler = StudentHandler(user, db)
		self.course_handler = CourseHandler(user, db)
		self.enrollment_handler = EnrollmentHandler(user, db)


	async def division_upload(self, regulation_id: int):
		content = await self.file.read()
		data = await xl_handler.extract_divisions(content)
		for d in data:
			d['regulation_id'] = regulation_id
			# if bool(d['private']):
			# 	r = Regulation(name=f"لائحة برنامج {d['name']}", max_gpa=5)
			# 	self.db.add(r)
			# 	await self.db.commit()
			# 	await self.db.refresh(r)
			# 	d['regulation_id'] = r.id
			try:
				d1 = await self.department_handler.get_by_name(d['department_1_id'])
				d['department_1_id'] = d1.id
			except:
				d['department_1_id'] = None
			try:
				d2 = await self.department_handler.get_by_name(d['department_2_id'])
				d['department_2_id'] = d2.id
			except:
				d['department_2_id'] = None
			division = Division(**d)
			self.db.add(division)
		await self.db.commit()
		return data


	async def course_upload(self):
		content = await self.file.read()
		data = await xl_handler.extract_courses(content)
		for d in data:
			course = Course(**{key: value for key, value in d.items() if key != 'division'})
			self.db.add(course)
			division = await self.division_handler.get_by_name(d['division'])
			course.divisions.append(division)
		await self.db.commit()
		return data


	async def enrollment_upload(self):
		content = await self.file.read()
		data = await xl_handler.final_dict(content)
		division = await self.division_handler.get_by_name(data['headers']['division'])
		response = []
		courses = dict()
		student = None
		for d in data['content']:
			#	if new student
			if not student or student.name != d['student']:
				#	if exists execute post_add_enrollment
				if student:
					await self.student_handler.post_add_enrollment(student)
				#	get the new student
				student = await self.student_handler.get_by_name_and_division(d['student'], division)
				if not student:
					response.append({'student': d['student'], 'course': d['course'], 'status': 'first year data does not exist'})
					continue
			#	get the course
			course = courses.get(d['code'])
			if not course:
				course = await self.course_handler.get_by_code_and_division_or_none(d['code'], division.id)
				if not course:
					response.append({'student': student.name, 'course': d['course'], 'status': 'course is not in the database'})
					continue
				courses[course.code] = course
			#	create enrollment if not exists
			enrollment = await self.enrollment_handler.get_or_create(data['headers'], d, student.id, course.id)
			if not enrollment:
				response.append({'student': student.name, 'course': course.name, 'status': 'enrollment already exists'})
				continue
			self.db.add(enrollment)
			student = await self.enrollment_handler.post_create(enrollment, student, course)
			response.append({'student': student.name, 'course': course.name, 'status': 'successfully added'})
		await self.db.commit()
		return response