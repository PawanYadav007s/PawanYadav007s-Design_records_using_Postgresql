from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class PORecord(db.Model):
    __tablename__ = 'po_records'

    id = db.Column(db.Integer, primary_key=True)
    po_number = db.Column(db.String(50), unique=True, nullable=False)
    
    quotation_number = db.Column(db.String(50), nullable=True)
    po_date = db.Column(db.Date, nullable=False)
    client_company_name = db.Column(db.String(100), nullable=False)
    project_name = db.Column(db.String(100), nullable=False)
    design_status = db.Column(db.String(50), default='pending')  # Added design_status to PORecord

    design_records = db.relationship(
        'DesignRecord',
        backref='po_record',
        lazy=True,
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<PORecord {self.po_number}>"

class DesignRecord(db.Model):
    __tablename__ = 'design_records'

    id = db.Column(db.Integer, primary_key=True)
    designer_name = db.Column(db.String(100), nullable=False)
    reference_design_location = db.Column(db.String(200), nullable=True)
    design_location = db.Column(db.String(200), nullable=False)
    design_release_date = db.Column(db.Date, nullable=False)

    po_id = db.Column(db.Integer, db.ForeignKey('po_records.id'), nullable=False)

    def __repr__(self):
        return f"<DesignRecord {self.designer_name} for PO {self.po_id}>"

class Designer(db.Model):
    __tablename__ = 'designers'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

    def __repr__(self):
        return f"<Designer {self.name}>"


class Quotation(db.Model):
    __tablename__ = 'quotations'

    id = db.Column(db.Integer, primary_key=True)
    quotation_number = db.Column(db.String(50), unique=True, nullable=False)
    quotation_date = db.Column(db.Date, nullable=False)
    quotation_details = db.Column(db.Text, nullable=False)
    design_location = db.Column(db.String(255), default='N/A', nullable=True)
    project_name = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(50), default='pending')

    def __repr__(self):
        return f"<Quotation {self.quotation_number}>"
