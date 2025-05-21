import os
from flask import Flask, render_template, request, redirect, url_for, send_file, flash
from models import db, PORecord, DesignRecord, Designer, Quotation
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from helpers import export_all_data_to_excel, load_settings, get_base_path, log_to_history_excel, update_quotation_master_excel
import pandas as pd
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "fallback-secret-key")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Use full connection string from environment
db_uri = os.getenv("DATABASE_URL")
if not db_uri:
    raise ValueError("❌ DATABASE_URL not found in environment!")
app.config['SQLALCHEMY_DATABASE_URI'] = db_uri

db.init_app(app)

def create_tables():
    with app.app_context():
        db.create_all()
        export_all_data_to_excel()

create_tables()


# Routes follow


@app.route('/')
def dashboard():
    """Dashboard summary showing pending POs."""
    pending_pos = PORecord.query.filter_by(design_status='pending').count()
    return render_template('dashboard.html', pending_pos=pending_pos)


@app.route('/add_po', methods=['GET', 'POST'])
def add_po():
    if request.method == 'POST':
        try:
            quotation_id = request.form.get('quotation_id')
            po_number = request.form['po_number']
            po_date = datetime.strptime(request.form['po_date'], '%Y-%m-%d').date()
            client_company_name = request.form['client_company_name']
            project_name = request.form['project_name']

            if quotation_id:
                quotation = Quotation.query.get(int(quotation_id))
                if not quotation:
                    flash('Selected quotation not found.', 'danger')
                    return redirect(url_for('add_po'))
                quotation_number = quotation.quotation_number
                quotation.status = 'used'
                db.session.add(quotation)  # <-- ADD THIS

            else:
                quotation_number = 'N/A'

            new_po = PORecord(
                po_number=po_number,
                quotation_number=quotation_number,
                po_date=po_date,
                client_company_name=client_company_name,
                project_name=project_name
            )

            db.session.add(new_po)
            db.session.commit()
            export_all_data_to_excel()
            update_quotation_master_excel()
            export_pending_quotations_excel()
            flash('PO Record added successfully!', 'success')

        except IntegrityError:
            db.session.rollback()
            flash('PO Number already exists.', 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('dashboard'))

    
    quotations = Quotation.query.filter_by(status='pending').order_by(Quotation.quotation_date.desc()).all()
    return render_template('add_po.html', quotations=quotations)    



@app.route('/view_pos')
def view_pos():
    pos = PORecord.query.order_by(PORecord.po_date.desc()).all()
    return render_template('view_pos.html', pos=pos)



@app.route('/delete_po/<int:po_id>', methods=['POST'])
def delete_po(po_id):
    po = PORecord.query.get_or_404(po_id)
    try:
        quotation_number = po.quotation_number  # store before deletion
        db.session.delete(po)
        db.session.commit()

        # Check if this quotation is still used in any other PO
        still_used = PORecord.query.filter_by(quotation_number=quotation_number).first()
        if not still_used:
            quotation = Quotation.query.filter_by(quotation_number=quotation_number).first()
            if quotation:
                quotation.status = 'pending'
                db.session.commit()

        export_all_data_to_excel()
        update_quotation_master_excel()
        export_pending_quotations_excel()
        flash('Purchase Order deleted successfully and quotation status released (if unused).', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting PO: {str(e)}', 'danger')
    return redirect(url_for('add_po'))




@app.route('/company_names')
def company_names():
    names = db.session.query(PORecord.client_company_name).distinct().all()
    name_list = [name[0] for name in names if name[0]]  # Extract strings
    return {'companies': name_list}



@app.route('/edit_po/<int:po_id>', methods=['POST'])
def edit_po(po_id):
    po = PORecord.query.get_or_404(po_id)
    po.po_number = request.form['po_number']
   

    # ✅ Convert string to Python date object
    po.po_date = datetime.strptime(request.form['po_date'], '%Y-%m-%d').date()

    po.client_company_name = request.form['client_company_name']
    po.project_name = request.form['project_name']
    
    db.session.commit()
    export_all_data_to_excel()
    flash('Purchase Order updated successfully!', 'success')
    return redirect(url_for('view_all'))







@app.route('/add_form', methods=['GET', 'POST'])
def add_form():
    """Route for designers to fill form based on available POs and select designer from dropdown."""
    if request.method == 'POST':
        try:
            po_number = request.form['po_number']
            po_record = PORecord.query.filter_by(po_number=po_number).first()

            new_design = DesignRecord(
                designer_name=request.form['designer_name'],
                reference_design_location=request.form['reference_design_location'],
                design_location=request.form['design_location'],
                design_release_date=datetime.strptime(request.form['design_release_date'], '%Y-%m-%d').date(),
                po_record=po_record
            )
            db.session.add(new_design)
            po_record.design_status = 'completed'
            db.session.commit()
            export_all_data_to_excel()
            log_to_history_excel('insert', new_design, po_record)

        except Exception as e:
            db.session.rollback()
            flash(f"Error submitting form: {e}", 'danger')
        return redirect(url_for('dashboard'))

    po_numbers = PORecord.query.filter_by(design_status='pending').all()
    designers = Designer.query.order_by(Designer.name).all()
    record = DesignRecord.query.first()  # Or find the specific record
    return render_template("add_form.html", po_numbers=po_numbers, designers=designers, record=record)






@app.route('/add_quotation', methods=['GET', 'POST'])
def add_quotation():
    error_msg = None

    if request.method == 'POST':
        quotation_id = request.form.get('quotation_id')  # For edit
        quotation_number = request.form['quotation_number']
        quotation_date = datetime.strptime(request.form['quotation_date'], '%Y-%m-%d').date()
        quotation_details = request.form['quotation_details']
        project_name = request.form['project_name']
        design_location = request.form.get('design_location') or "N/A"

        if quotation_id:  # Update existing
            quotation = Quotation.query.get(int(quotation_id))
            if quotation:
                if quotation.quotation_number != quotation_number:
                    existing = Quotation.query.filter_by(quotation_number=quotation_number).first()
                    if existing:
                        error_msg = f"Quotation Number '{quotation_number}' already exists."
                if not error_msg:
                    quotation.quotation_number = quotation_number
                    quotation.quotation_date = quotation_date
                    quotation.quotation_details = quotation_details
                    quotation.project_name = project_name
                    quotation.design_location = design_location
                    flash('Quotation updated successfully!', 'success')

        else:  # Add new
            existing = Quotation.query.filter_by(quotation_number=quotation_number).first()
            if existing:
                error_msg = f"Quotation Number '{quotation_number}' already exists. Please use a unique number."
            else:
                new_quotation = Quotation(
                    quotation_number=quotation_number,
                    quotation_date=quotation_date,
                    quotation_details=quotation_details,
                    project_name=project_name,
                    design_location=design_location
                )
                db.session.add(new_quotation)
                flash('Quotation added successfully!', 'success')

        if error_msg:
            quotations = Quotation.query.order_by(Quotation.quotation_date.desc()).all()
            return render_template('add_quotation.html', quotations=quotations, error_msg=error_msg)

        db.session.commit()
        return redirect(url_for('add_quotation'))

    quotations = Quotation.query.order_by(Quotation.quotation_date.desc()).all()
    return render_template('add_quotation.html', quotations=quotations)




@app.route('/quotation_status')
def quotation_status():
    query = request.args.get('query', '')

    if query:
        pending_quotations = Quotation.query.filter(
            Quotation.status == 'pending',
            db.or_(
                Quotation.quotation_number.ilike(f"%{query}%"),
                Quotation.project_name.ilike(f"%{query}%"),
                Quotation.quotation_details.ilike(f"%{query}%"),
                Quotation.design_location.ilike(f"%{query}%")
            )
        ).order_by(Quotation.quotation_date.desc()).all()
    else:
        pending_quotations = Quotation.query.filter_by(status='pending')\
                                            .order_by(Quotation.quotation_date.desc()).all()

    return render_template('quotation_status.html', pending_quotations=pending_quotations)




@app.route('/manage_quotations')
def manage_quotations():
    quotations = Quotation.query.all()
    return render_template('add_quotation.html', quotations=quotations)

@app.route('/quotation_list')
def quotation_list():
    quotations = Quotation.query.order_by(Quotation.quotation_date.desc()).all()
    return render_template('quotation_list.html', quotations=quotations)

@app.route('/delete_quotation/<int:quotation_id>', methods=['POST'])
def delete_quotation(quotation_id):
    quotation = Quotation.query.get_or_404(quotation_id)
    db.session.delete(quotation)
    db.session.commit()
    flash('Quotation deleted successfully!', 'warning')
    return redirect(url_for('add_quotation'))




@app.route('/designers', methods=['GET', 'POST'])
def manage_designers():
    if request.method == 'POST':
        name = request.form['designer_name'].strip()
        if name:
            existing = Designer.query.filter_by(name=name).first()
            if not existing:
                db.session.add(Designer(name=name))
                db.session.commit()
            else:
                flash("Designer already exists.", "warning")
        return redirect(url_for('manage_designers'))

    designers = Designer.query.order_by(Designer.name).all()
    return render_template('manage_designers.html', designers=designers)

@app.route('/delete_designer/<int:designer_id>', methods=['POST'])
def delete_designer(designer_id):
    designer = Designer.query.get_or_404(designer_id)
    db.session.delete(designer)
    db.session.commit()
    return redirect(url_for('manage_designers'))

@app.route('/edit_designer/<int:designer_id>', methods=['POST'])
def edit_designer(designer_id):
    designer = Designer.query.get_or_404(designer_id)
    new_name = request.form['new_name'].strip()
    if new_name:
        designer.name = new_name
        db.session.commit()
    return redirect(url_for('manage_designers'))




@app.route('/view_all')
def view_all():
    query = request.args.get('query', '').strip()
    if query:
        records = db.session.query(DesignRecord, PORecord).join(PORecord).filter(
             (PORecord.po_number.ilike(f'%{query}%')) |
        (PORecord.project_name.ilike(f'%{query}%')) |
        (PORecord.client_company_name.ilike(f'%{query}%')) |
        (PORecord.po_date.ilike(f'%{query}%')) |
       (DesignRecord.design_release_date.ilike(f'%{query}%')) |
        (DesignRecord.designer_name.ilike(f'%{query}%'))
    ).order_by(DesignRecord.design_release_date.desc()).all()
    else:
        records = db.session.query(DesignRecord, PORecord).join(PORecord).order_by(DesignRecord.id.desc()).all()
    return render_template('view_all.html', records=records, query=query)


@app.route('/search')
def search():
    """Search design records by multiple fields."""
    query = request.args.get('query', '')
    records = db.session.query(DesignRecord, PORecord).join(PORecord).filter(
        (PORecord.po_number.ilike(f'%{query}%')) |
        (PORecord.project_name.ilike(f'%{query}%')) |
        (PORecord.client_company_name.ilike(f'%{query}%')) |
        (PORecord.po_date.ilike(f'%{query}%')) |
       (DesignRecord.design_release_date.ilike(f'%{query}%')) |
        (DesignRecord.designer_name.ilike(f'%{query}%'))
    ).order_by(DesignRecord.design_release_date.desc()).all() if query else []
    return render_template('search.html', records=records, query=query)

@app.route('/edit/<int:record_id>', methods=['GET', 'POST'])
def edit_record(record_id):
    """Edit a design record."""
    record = DesignRecord.query.get_or_404(record_id)
    designers = Designer.query.order_by(Designer.name).all()
    po_list = PORecord.query.order_by(PORecord.id.desc()).all()  # Latest first PO list

    if request.method == 'POST':
        try:
            # Validate and assign PO
            po_id = int(request.form['po_id'])
            po = PORecord.query.get(po_id)
            if not po:
                flash('Invalid PO selected.', 'danger')
                return redirect(url_for('edit_record', record_id=record_id))
            record.po_id = po_id

            record.designer_name = request.form['designer_name']
            record.reference_design_location = request.form['reference_design_location']
            record.design_location = request.form['design_location']
            record.design_release_date = datetime.strptime(request.form['design_release_date'], '%Y-%m-%d').date()

            db.session.commit()

            export_all_data_to_excel()
            log_to_history_excel('update', record, record.po_record)

            flash('Design record updated.', 'success')
            return redirect(url_for('view_all'))

        except Exception as e:
            db.session.rollback()
            flash(f"Error updating record: {e}", 'danger')
            return redirect(url_for('edit_record', record_id=record_id))

    return render_template(
        'edit_record.html',
        record=record,
        designers=designers,
        po_list=po_list
    )





@app.route('/delete/<int:record_id>')
def delete_record(record_id):
    try:
        # Get the design record to delete
        record = DesignRecord.query.get_or_404(record_id)
        # Get the parent PO
        po = PORecord.query.get_or_404(record.po_id)
        quotation_number = po.quotation_number

        # Optional: log deletion (your existing function)
        log_to_history_excel('delete', record, po)

        # Delete the entire PO (will cascade to design records)
        db.session.delete(po)
        db.session.commit()

        # Update quotation status if needed
        if quotation_number != 'N/A':
            quotation = Quotation.query.filter_by(quotation_number=quotation_number).first()
            if quotation:
                # Check if any other PO uses this quotation
                po_using_quotation = PORecord.query.filter(
                    PORecord.quotation_number == quotation_number
                ).count()

                if po_using_quotation == 0:
                    quotation.status = 'pending'
                    db.session.add(quotation)
                    db.session.commit()
                    flash(f"Quotation {quotation_number} marked as pending again.")

        export_all_data_to_excel()
        flash('PO and all related design records deleted successfully.', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting record: {e}", 'danger')

    return redirect(url_for('view_all'))




@app.route('/export_excel')
def export_excel():
    """Download all design records as an Excel file."""
    try:
        records = db.session.query(DesignRecord, PORecord).join(PORecord).all()
        data = [[
            i+1,
            po.po_number,
            po.po_date,
            po.project_name,
            po.client_company_name,
            dr.designer_name,
            dr.reference_design_location,
            dr.design_location,
            dr.design_release_date
        ] for i, (dr, po) in enumerate(records)]

        df = pd.DataFrame(data, columns=[
            'Sr.No', 'PO Number', 'PO Date', 'Project Name', 'Client Company Name',
            'Designer Name', 'Reference Design', 'Design Location', 'Design Release Date'
        ])

        filename = f"design_records_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        download_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        filepath = os.path.join(download_dir, filename)
        df.to_excel(filepath, index=False)

        return send_file(filepath, as_attachment=True)
    except Exception as e:
        flash(f"Error exporting Excel file: {str(e)}", 'danger')
        return redirect(url_for('dashboard'))









@app.route('/export_pending_quotations_excel')
def export_pending_quotations_excel():
    try:
        # Step 1: Collect used quotation numbers
        used_quotation_numbers = [po.quotation_number for po in PORecord.query.all()]
        
        # Step 2: Get current pending quotations
        pending_quotations = Quotation.query.filter(
            Quotation.status == 'pending',
            ~Quotation.quotation_number.in_(used_quotation_numbers)
        ).all()

        # Step 3: Convert to DataFrame
        df_new = pd.DataFrame([{
            'Quotation No': q.quotation_number,
            'Date': q.quotation_date.strftime('%Y-%m-%d'),
            'Details': q.quotation_details,
            'Project': q.project_name,
            'Location': q.design_location,
            'Status': q.status
        } for q in pending_quotations])

        # Step 4: Get path from settings
        settings = load_settings()
        save_path = settings["excel_save_path"]
        master_file = os.path.join(save_path, 'pending_quotations_master.xlsx')

        os.makedirs(save_path, exist_ok=True)  # Ensure folder exists

        # Step 5: Append/update existing file if it exists
        if os.path.exists(master_file):
            df_existing = pd.read_excel(master_file)
            df_combined = pd.concat([df_existing, df_new])
            df_combined.drop_duplicates(subset='Quotation No', keep='last', inplace=True)
        else:
            df_combined = df_new

        # Step 6: Save permanent file
        df_combined.to_excel(master_file, index=False)
        print(f"[INFO] Permanent pending quotations saved at: {master_file}")

        # Step 7: Also generate a download copy (fresh only pending ones)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        download_filename = f"pending_unused_quotations_{timestamp}.xlsx"
        download_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        os.makedirs(download_dir, exist_ok=True)
        download_path = os.path.join(download_dir, download_filename)
        df_new.to_excel(download_path, index=False)

        return send_file(download_path, as_attachment=True)

    except Exception as e:
        import traceback
        print(f"[ERROR] Export failed: {e}")
        traceback.print_exc()
        return "Error exporting file", 500








if __name__ == '__main__':
    create_tables()
    app.run(host='0.0.0.0', port=9000, debug=False)


