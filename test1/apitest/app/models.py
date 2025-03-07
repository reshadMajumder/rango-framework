from rango.models import Model, IntegerField, TextField, DateTimeField

class User(Model):
    id = IntegerField(primary_key=True)
    name = TextField(null=False)
    email = TextField(null=False, unique=True)

    class Meta:
        table_name = 'users'

class Product(Model):
    id = IntegerField(primary_key=True)
    name = TextField(null=False)
    price = IntegerField(null=False)
    created_at = DateTimeField(auto_now=True)

    class Meta:
        table_name = 'products'

def init_db():
    """Initialize database tables"""
    User.create_table()
    Product.create_table()

if __name__ == "__main__":
    init_db() 