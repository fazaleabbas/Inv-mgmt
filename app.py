# app.py
from flask import Flask, render_template, request, redirect, url_for, flash
from extensions import db, login_manager # Import db and login_manager from extensions
from models import Item, Sale, User
from datetime import datetime
from auth import auth  # Import auth blueprint
from flask_login import LoginManager, login_required, current_user

import qrcode
import os


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///inventory.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = '215/b/2STApartments'  # Add a unique secret key here


# Initialize db and login_manager
db.init_app(app)
login_manager.init_app(app)

# Register the Blueprint for authentication
app.register_blueprint(auth, url_prefix='/auth')

    
# Ensure db tables are created
with app.app_context():
    db.create_all()

# Ensure user_loader is set in app.py
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/inventory')
@login_required
def inventory():
    items = Item.query.all()
    return render_template('inventory.html', items=items)
    

@app.route('/sales')
@login_required
def sales():
    sales = Sale.query.all()
    items = Item.query.all()  # Pass items to use in the dropdown form in sales.html
    return render_template('sales.html', sales=sales, items=items)

@app.route('/add', methods=['POST'])
@login_required
def add_item():
    name = request.form['name']
    desc = request.form['desc']
    quantity = int(request.form['quantity'])
    price = float(request.form['price'])
    new_item = Item(name=name, desc=desc, quantity=quantity, price=price)
    db.session.add(new_item)
    db.session.commit()
    
    # Generate QR code
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(f"Item ID: {new_item.id}, Name: {new_item.name}, Quantity: {new_item.quantity}")
    qr.make(fit=True)
    img = qr.make_image(fill='black', back_color='white')

    # Ensure qr_codes directory exists
    qr_code_dir = os.path.join('static', 'qr_codes')
    os.makedirs(qr_code_dir, exist_ok=True)
    qr_code_path = os.path.join(qr_code_dir, f'item_{new_item.id}.png')
    img.save(qr_code_path)

    return redirect(url_for('inventory'))
    
@app.route('/delete/<int:id>')
@login_required
def delete_item(id):
    item = Item.query.get(id)
    
    # Check if there are any sales associated with this item
    if item.sales:
        # Flash a message to the user about the dependency
        flash("Cannot delete item because there are completed sales orders against it.")
        return redirect(url_for('inventory'))
        
    # Proceed with deletion if no associated sales
    db.session.delete(item)
    db.session.commit()
    flash('Item successfully deleted.', 'success')
    #else:
        # Optionally, add a flash message or error handling here
    #    print(f"Item with id {id} does not exist.")
        #flash('Item not found!', 'error')

    return redirect(url_for('inventory'))
    
    
@app.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_item(id):
    item = Item.query.get_or_404(id)
    
    if request.method == 'POST':
        # Update item details with form data
        item.name = request.form['name']
        item.desc = request.form['desc']
        item.quantity = int(request.form['quantity'])
        item.price = float(request.form['price'])
        
        db.session.commit()
        return redirect(url_for('inventory'))
    
    return render_template('edit_item.html', item=item)


@app.route('/sell', methods=['POST'])
@login_required
def sell_item():
    item_id = int(request.form['item_id'])
    quantity_sold = int(request.form['quantity'])
    item = Item.query.get(item_id)

    if item and item.quantity >= quantity_sold:
        item.quantity -= quantity_sold
        sale = Sale(item_id=item.id, quantity_sold=quantity_sold)
        db.session.add(sale)
        db.session.commit()
        flash('Sale recorded successfully!', 'success')
    else:
        # Flash a message if the item quantity is insufficient
        if item:
            flash('Error: Insufficient quantity in stock.', 'error')
        else:
            flash('Error: Item not found.', 'error')
        return redirect(url_for('inventory'))

    return redirect(url_for('sales'))

if __name__ == "__main__":
    app.run(debug=True)
