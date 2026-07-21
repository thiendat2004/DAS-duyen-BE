uvicorn app.main:app --reload


python -m alembic init alembic -> khởi tạo alembic -> migrate / cập nhật db
|_python -m alembic revision --autogenerate -m "add auth fields" -> python -m alembic upgrade head