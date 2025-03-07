from typing import Any, Dict, List, Type, TypeVar, Optional
from datetime import datetime
from aiohttp import web
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T', bound='Model')

class Field:
    def __init__(self, field_type: str, null: bool = False, unique: bool = False, primary_key: bool = False):
        self.field_type = field_type
        self.null = null
        self.unique = unique
        self.primary_key = primary_key

    def get_sql_definition(self) -> str:
        sql = self.field_type
        if self.primary_key:
            sql += " PRIMARY KEY"
        if not self.null:
            sql += " NOT NULL"
        if self.unique:
            sql += " UNIQUE"
        return sql

class IntegerField(Field):
    def __init__(self, null: bool = False, unique: bool = False, primary_key: bool = False):
        super().__init__("INTEGER", null, unique, primary_key)

class TextField(Field):
    def __init__(self, null: bool = False, unique: bool = False):
        super().__init__("TEXT", null, unique)

class DateTimeField(Field):
    def __init__(self, auto_now: bool = False, null: bool = False):
        super().__init__("TIMESTAMP", null)
        self.auto_now = auto_now

class QuerySet:
    def __init__(self, model_class: Type[T], db):
        self.model_class = model_class
        self.db = db
        self._where = []
        self._params = []
        self._order_by = []
        self._limit = None
        self._offset = None

    def filter(self, **kwargs) -> 'QuerySet[T]':
        conditions = []
        params = []
        for key, value in kwargs.items():
            if '__' in key:
                field, op = key.split('__')
                if op == 'gt':
                    conditions.append(f"{field} > ?")
                elif op == 'lt':
                    conditions.append(f"{field} < ?")
                elif op == 'gte':
                    conditions.append(f"{field} >= ?")
                elif op == 'lte':
                    conditions.append(f"{field} <= ?")
                elif op == 'contains':
                    conditions.append(f"{field} LIKE ?")
                    value = f"%{value}%"
                elif op == 'in':
                    placeholders = ','.join(['?' for _ in value])
                    conditions.append(f"{field} IN ({placeholders})")
                    params.extend(value)
                    continue
            else:
                conditions.append(f"{key} = ?")
            params.append(value)

        self._where.extend(conditions)
        self._params.extend(params)
        return self

    def order_by(self, *fields) -> 'QuerySet[T]':
        for field in fields:
            if field.startswith('-'):
                self._order_by.append(f"{field[1:]} DESC")
            else:
                self._order_by.append(f"{field} ASC")
        return self

    def limit(self, limit: int) -> 'QuerySet[T]':
        self._limit = limit
        return self

    def offset(self, offset: int) -> 'QuerySet[T]':
        self._offset = offset
        return self

    def _build_query(self, select: str = "*") -> tuple[str, list]:
        query = f"SELECT {select} FROM {self.model_class._meta.table_name}"
        
        if self._where:
            query += " WHERE " + " AND ".join(self._where)
            
        if self._order_by:
            query += " ORDER BY " + ", ".join(self._order_by)
            
        if self._limit is not None:
            query += f" LIMIT {self._limit}"
            
        if self._offset is not None:
            query += f" OFFSET {self._offset}"
            
        return query, self._params

    def all(self) -> List[T]:
        query, params = self._build_query()
        rows = self.db.query(query, tuple(params))
        return [self.model_class(**row) for row in rows]

    def first(self) -> Optional[T]:
        self._limit = 1
        results = self.all()
        return results[0] if results else None

    def count(self) -> int:
        query, params = self._build_query("COUNT(*)")
        result = self.db.get_one(query, tuple(params))
        return result['COUNT(*)']

class ModelMeta:
    def __init__(self, table_name: str, fields: Dict[str, Field]):
        self.table_name = table_name
        self.fields = fields

class Model:
    class Meta:
        abstract = True

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    @classmethod
    def _init_meta(cls):
        if not hasattr(cls, '_meta'):
            fields = {}
            for name, value in cls.__dict__.items():
                if isinstance(value, Field):
                    fields[name] = value
            
            table_name = getattr(cls.Meta, 'table_name', cls.__name__.lower())
            cls._meta = ModelMeta(table_name, fields)

    @classmethod
    def objects(cls) -> QuerySet:
        from .app import get_app
        app = get_app()
        cls._init_meta()
        return QuerySet(cls, app.orm)

    def save(self):
        try:
            self._init_meta()
            data = {}
            
            # Prepare data for save
            for name, field in self._meta.fields.items():
                # Skip id for new records or if it's None
                if name == 'id':
                    if not hasattr(self, 'id') or self.id is None:
                        continue
                
                value = getattr(self, name, None)
                if isinstance(field, DateTimeField) and field.auto_now:
                    value = datetime.now()
                if value is not None or field.null:
                    data[name] = value

            db = self.objects().db
            
            if hasattr(self, 'id') and self.id:
                # Check if record exists before update
                exists = db.get_one(
                    f"SELECT 1 FROM {self._meta.table_name} WHERE id = ?",
                    (self.id,)
                )
                if exists:
                    # Update existing record
                    db.update(
                        self._meta.table_name,
                        data,
                        "id = ?",
                        (self.id,)
                    )
                else:
                    # Insert with specified ID
                    self.id = db.insert(self._meta.table_name, data)
            else:
                # Insert new record
                if 'id' in data:
                    del data['id']
                self.id = db.insert(self._meta.table_name, data)

            # Verify the save by refreshing from database
            saved_data = db.get_one(
                f"SELECT * FROM {self._meta.table_name} WHERE id = ?",
                (self.id,)
            )
            
            if not saved_data:
                raise Exception("Failed to save record")

            # Update instance with saved data
            for key, value in saved_data.items():
                setattr(self, key, value)

            return self
        except Exception as e:
            logger.error(f"Save error: {str(e)}")
            if isinstance(e, web.HTTPException):
                raise
            raise web.HTTPBadRequest(text=str(e))

    def delete(self):
        try:
            if hasattr(self, 'id'):
                self.objects().db.delete(
                    self._meta.table_name,
                    "id = ?",
                    (self.id,)
                )
        except Exception as e:
            logger.error(f"Delete error: {str(e)}")
            raise web.HTTPBadRequest(text=str(e))

    @classmethod
    def create_table(cls):
        try:
            cls._init_meta()
            from .app import get_app
            app = get_app()
            columns = {
                name: field.get_sql_definition()
                for name, field in cls._meta.fields.items()
            }
            app.orm.create_table(cls._meta.table_name, columns)
        except Exception as e:
            logger.error(f"Create table error: {str(e)}")
            raise web.HTTPBadRequest(text=str(e))

    def to_dict(self):
        """Convert model instance to dictionary"""
        return {
            name: getattr(self, name)
            for name in self._meta.fields.keys()
            if hasattr(self, name)
        } 