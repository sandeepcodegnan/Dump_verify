"""
Template Service Layer - Business Logic (SoC)
Handles all template operations and validation
"""
from datetime import datetime
from .s3_utils import S3Utils
from .sql_parser import SQLParser
from web.Exam.exam_central_db import mysql_templates_collection

class TemplateService:
    def __init__(self):
        self.s3_utils = S3Utils()
        self.sql_parser = SQLParser()
    
    def get_template(self, template_id):
        """Get template by ID - DRY principle"""
        template = mysql_templates_collection.find_one({"_id": template_id})
        if not template:
            raise ValueError("Template not found")
        return template
    
    def validate_tables_exist(self, template, table_names):
        """Validate tables exist in template - DRY principle"""
        template_tables = template.get("tables", [])
        missing_tables = [t for t in table_names if t not in template_tables]
        if missing_tables:
            raise ValueError(f"Tables not found: {missing_tables}")
    
    def upload_template(self, template_name, description, sql_content):
        """Upload template to S3 and MongoDB"""
        # Extract table names
        tables = self.sql_parser.extract_table_names(sql_content)
        
        # Upload to S3
        sql_url = self.s3_utils.upload_sql_content(template_name, sql_content)
        
        # Save to MongoDB
        template_doc = {
            "_id": template_name,
            "name": template_name,
            "description": description,
            "tables": tables,
            "s3_sql_url": sql_url,
            "created_at": datetime.utcnow(),
            "status": "active"
        }
        
        mysql_templates_collection.replace_one(
            {"_id": template_name}, 
            template_doc, 
            upsert=True
        )
        
        return template_name
    
    def list_templates(self):
        """Get all active templates"""
        templates = list(mysql_templates_collection.find(
            {"status": "active"}, 
            {"name": 1, "tables": 1}
        ))
        
        # Convert ObjectId to string
        for template in templates:
            template["template_id"] = str(template["_id"])
            del template["_id"]
        
        return templates
    
    def get_table_names(self, template_id):
        """Get table names for template"""
        template = self.get_template(template_id)
        return {
            "template_id": template_id,
            "template_name": template.get("name"),
            "tables": template.get("tables", [])
        }
    
    def get_table_data(self, template_id, table_names):
        """Get table data for single or multiple tables"""
        template = self.get_template(template_id)
        self.validate_tables_exist(template, table_names)
        
        # Get SQL content
        sql_content = self.s3_utils.get_file_content(f"{template_id}/complete.sql")
        
        # Build consistent response for both single and multiple tables
        tables_data = {}
        combined_sql = ""
        
        for table_name in table_names:
            table_data = self.sql_parser.parse_table(sql_content, table_name)
            tables_data[table_name] = {
                "schema": table_data["schema"],
                "data": table_data["data"]
            }
            combined_sql += table_data["raw_sql"] + "\n\n"
        
        response = {
            "template_id": template_id,
            "tables": table_names,
            "tables_data": tables_data
        }
        
        # Use raw_table_sql for both single and multiple tables
        response["raw_table_sql"] = combined_sql.strip()
        
        return response