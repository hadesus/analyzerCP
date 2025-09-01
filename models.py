from extensions import db
from datetime import datetime

class Analysis(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    upload_timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Relationship to DrugResult
    drug_results = db.relationship('DrugResult', backref='analysis', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Analysis {self.filename}>'

class DrugResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    analysis_id = db.Column(db.Integer, db.ForeignKey('analysis.id'), nullable=False)

    # --- Data Fields ---
    # From protocol
    inn_protocol = db.Column(db.String(255))
    usage_protocol = db.Column(db.Text)
    loe_protocol = db.Column(db.String(50))

    # AI-generated fields
    brief_description = db.Column(db.Text)

    # Processed data
    inn_english = db.Column(db.String(255))
    parsed_dosage = db.Column(db.String(50))
    parsed_units = db.Column(db.String(50))
    parsed_frequency = db.Column(db.String(100))
    normalized_route = db.Column(db.String(100))

    # Verification results
    who_eml_status = db.Column(db.String(50))
    fda_status = db.Column(db.String(50))
    ema_status = db.Column(db.String(50))
    pubmed_links = db.Column(db.Text) # Storing links separated by newline
    system_loe = db.Column(db.String(50))

    def __repr__(self):
        return f'<DrugResult {self.inn_protocol} for Analysis {self.analysis_id}>'
