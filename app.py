
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, DecimalField, IntegerField, SelectField, TextAreaField, DateField
from wtforms.validators import DataRequired, Email, NumberRange
from datetime import datetime, date
import os
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import func, extract, Numeric # Import Numeric from sqlalchemy

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///sales_company.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Database Models
class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    orders = db.relationship('Order', backref='customer', lazy=True)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Text
    price = db.Column(db.Numeric(10, 2), nullable=False)
    stock_quantity = db.Column(db.Integer, default=0)
    category = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    order_date = db.Column(db.Date, default=date.today)
    total_amount = db.Column(db.Numeric(10, 2), default=0)
    status = db.Column(db.String(20), default='pending')
    notes = db.Column(db.Text)
    items = db.relationship('OrderItem', backref='order', lazy=True, cascade='all, delete-orphan')

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    product = db.relationship('Product', backref='order_items')

# Forms
class CustomerForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Phone')
    address = TextAreaField('Address')

class ProductForm(FlaskForm):
    name = StringField('Product Name', validators=[DataRequired()])
    description = TextAreaField('Description')
    price = DecimalField('Price', validators=[DataRequired(), NumberRange(min=0)])
    stock_quantity = IntegerField('Stock Quantity', validators=[NumberRange(min=0)])
    category = StringField('Category')

class OrderForm(FlaskForm):
    customer_id = SelectField('Customer', coerce=int, validators=[DataRequired()])
    order_date = DateField('Order Date', default=date.today)
    status = SelectField('Status', choices=[
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled')
    ])
    notes = TextAreaField('Notes')

# Routes
@app.route('/')
def dashboard():
    total_customers = Customer.query.count()
    total_products = Product.query.count()
    total_orders = Order.query.count()

    recent_orders = Order.query.order_by(Order.order_date.desc()).limit(5).all()

    # Monthly sales data
    from sqlalchemy import func, extract
    monthly_sales = db.session.query(
        extract('month', Order.order_date).label('month'),
        func.sum(Order.total_amount).label('total')
    ).group_by(extract('month', Order.order_date)).all()

    return render_template('dashboard.html',
                         total_customers=total_customers,
                         total_products=total_products,
                         total_orders=total_orders,
                         recent_orders=recent_orders,
                         monthly_sales=monthly_sales)

# Customer Routes
@app.route('/customers')
def customers():
    page = request.args.get('page', 1, type=int)
    customers = Customer.query.paginate(
        page=page, per_page=10, error_out=False
    )
    return render_template('customers.html', customers=customers)

@app.route('/customers/add', methods=['GET', 'POST'])
def add_customer():
    form = CustomerForm()
    if form.validate_on_submit():
        customer = Customer(
            name=form.name.data,
            email=form.email.data,
            phone=form.phone.data,
            address=form.address.data
        )
        db.session.add(customer)
        db.session.commit()
        flash('Customer added successfully!', 'success')
        return redirect(url_for('customers'))
    return render_template('customer_form.html', form=form, title='Add Customer')

@app.route('/customers/<int:id>/edit', methods=['GET', 'POST'])
def edit_customer(id):
    customer = Customer.query.get_or_404(id)
    form = CustomerForm(obj=customer)
    if form.validate_on_submit():
        form.populate_obj(customer)
        db.session.commit()
        flash('Customer updated successfully!', 'success')
        return redirect(url_for('customers'))
    return render_template('customer_form.html', form=form, title='Edit Customer')

@app.route('/customers/<int:id>/delete', methods=['POST'])
def delete_customer(id):
    customer = Customer.query.get_or_404(id)
    db.session.delete(customer)
    db.session.commit()
    flash('Customer deleted successfully!', 'success')
    return redirect(url_for('customers'))

# Product Routes
@app.route('/products')
def products():
    page = request.args.get('page', 1, type=int)
    products = Product.query.paginate(
        page=page, per_page=10, error_out=False
    )
    return render_template('products.html', products=products)

@app.route('/products/add', methods=['GET', 'POST'])
def add_product():
    form = ProductForm()
    if form.validate_on_submit():
        product = Product(
            name=form.name.data,
            description=form.description.data,
            price=form.price.data,
            stock_quantity=form.stock_quantity.data,
            category=form.category.data
        )
        db.session.add(product)
        db.session.commit()
        flash('Product added successfully!', 'success')
        return redirect(url_for('products'))
    return render_template('product_form.html', form=form, title='Add Product')

@app.route('/products/<int:id>/edit', methods=['GET', 'POST'])
def edit_product(id):
    product = Product.query.get_or_404(id)
    form = ProductForm(obj=product)
    if form.validate_on_submit():
        form.populate_obj(product)
        db.session.commit()
        flash('Product updated successfully!', 'success')
        return redirect(url_for('products'))
    return render_template('product_form.html', form=form, title='Edit Product')

@app.route('/products/<int:id>/delete', methods=['POST'])
def delete_product(id):
    product = Product.query.get_or_404(id)
    db.session.delete(product)
    db.session.commit()
    flash('Product deleted successfully!', 'success')
    return redirect(url_for('products'))

# Order Routes
@app.route('/orders')
def orders():
    page = request.args.get('page', 1, type=int)
    orders = Order.query.order_by(Order.order_date.desc()).paginate(
        page=page, per_page=10, error_out=False
    )
    return render_template('orders.html', orders=orders)

@app.route('/orders/add', methods=['GET', 'POST'])
def add_order():
    form = OrderForm()
    form.customer_id.choices = [(c.id, c.name) for c in Customer.query.all()]

    if form.validate_on_submit():
        order = Order(
            customer_id=form.customer_id.data,
            order_date=form.order_date.data,
            status=form.status.data,
            notes=form.notes.data
        )
        db.session.add(order)
        db.session.commit()
        flash('Order created successfully!', 'success')
        return redirect(url_for('edit_order', id=order.id))

    return render_template('order_form.html', form=form, title='Create Order')

@app.route('/orders/<int:id>')
def view_order(id):
    order = Order.query.get_or_404(id)
    return render_template('order_detail.html', order=order)

@app.route('/orders/<int:id>/edit', methods=['GET', 'POST'])
def edit_order(id):
    order = Order.query.get_or_404(id)
    form = OrderForm(obj=order)
    form.customer_id.choices = [(c.id, c.name) for c in Customer.query.all()]

    if form.validate_on_submit():
        form.populate_obj(order)
        db.session.commit()
        flash('Order updated successfully!', 'success')
        return redirect(url_for('orders'))

    products = Product.query.all()
    return render_template('order_edit.html', form=form, order=order, products=products, title='Edit Order')

@app.route('/orders/<int:order_id>/items/add', methods=['POST'])
def add_order_item(order_id):
    order = Order.query.get_or_404(order_id)
    product_id = request.form.get('product_id', type=int)
    quantity = request.form.get('quantity', type=int)

    product = Product.query.get_or_404(product_id)

    if product.stock_quantity < quantity:
        flash('Insufficient stock!', 'error')
        return redirect(url_for('edit_order', id=order_id))

    order_item = OrderItem(
        order_id=order_id,
        product_id=product_id,
        quantity=quantity,
        unit_price=product.price
    )

    # Update stock
    product.stock_quantity -= quantity

    db.session.add(order_item)

    # Recalculate order total
    order.total_amount = sum(item.quantity * item.unit_price for item in order.items) + (quantity * product.price)

    db.session.commit()
    flash('Item added to order!', 'success')
    return redirect(url_for('edit_order', id=order_id))

@app.route('/orders/<int:order_id>/items/<int:item_id>/delete', methods=['POST'])
def delete_order_item(order_id, item_id):
    order = Order.query.get_or_404(order_id)
    item = OrderItem.query.get_or_404(item_id)

    # Return stock
    product = item.product
    product.stock_quantity += item.quantity

    db.session.delete(item)

    # Recalculate order total
    remaining_items = [i for i in order.items if i.id != item_id]
    order.total_amount = sum(i.quantity * i.unit_price for i in remaining_items)

    db.session.commit()
    flash('Item removed from order!', 'success')
    return redirect(url_for('edit_order', id=order_id))

# Analytics Routes
@app.route('/analytics')
def analytics():
    from sqlalchemy import func

    # Top selling products
    top_products = db.session.query(
        Product.name,
        func.sum(OrderItem.quantity).label('total_sold')
    ).join(OrderItem).group_by(Product.name).order_by(func.sum(OrderItem.quantity).desc()).limit(10).all()

    # Sales by status
    status_stats = db.session.query(
        Order.status,
        func.count(Order.id).label('count'),
        func.sum(Order.total_amount).label('total')
    ).group_by(Order.status).all()

    return render_template('analytics.html', top_products=top_products, status_stats=status_stats)

# API Routes
@app.route('/api/customers')
def api_customers():
    customers = Customer.query.all()
    return jsonify([{
        'id': c.id,
        'name': c.name,
        'email': c.email,
        'phone': c.phone
    } for c in customers])

@app.route('/api/products')
def api_products():
    products = Product.query.all()
    return jsonify([{
        'id': p.id,
        'name': p.name,
        'price': float(p.price),
        'stock': p.stock_quantity
    } for p in products])

# Error Handlers
@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500

# Initialize database
@app.before_request
def create_tables():
    if not hasattr(create_tables, '_first_request_handled'):
        db.create_all()
        # Add sample data if database is empty
        if Customer.query.count() == 0:
            sample_customer = Customer(
                name='John Doe',
                email='john@example.com',
                phone='123-456-7890',
                address='123 Main St, City, State'
            )

            sample_product = Product(
                name='Sample Product',
                description='This is a sample product',
                price=29.99,
                stock_quantity=100,
                category='Electronics'
            )

            db.session.add(sample_customer)
            db.session.add(sample_product)
            db.session.commit()
        create_tables._first_request_handled = True


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=os.environ.get('FLASK_ENV') == 'development')

