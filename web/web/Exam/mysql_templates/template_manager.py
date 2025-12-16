from flask import request
from flask_restful import Resource
from web.jwt.auth_middleware import admin_required,tester_required
from .template_service import TemplateService
from .api_response import APIResponse

class TemplateUpload(Resource):
    def __init__(self):
        self.service = TemplateService()
    
    @admin_required
    def post(self):
        """Upload complete SQL template file to S3 and register in MongoDB"""
        try:
            # Validate request
            template_name = request.form.get('template_name')
            if not template_name:
                return APIResponse.error("Template name required")
            
            sql_file = self._get_sql_file()
            if not sql_file:
                return APIResponse.error("SQL file required")
            
            if not sql_file.filename.endswith('.sql'):
                return APIResponse.error("File must be .sql")
            
            # Process upload
            sql_content = sql_file.read().decode('utf-8')
            description = request.form.get('description', '')
            
            template_id = self.service.upload_template(template_name, description, sql_content)
            
            return APIResponse.success({
                "message": f"Template '{template_name}' uploaded successfully",
                "template_id": template_id
            }, 201)
            
        except Exception as e:
            return APIResponse.server_error(f"Upload failed: {str(e)}")
    
    def _get_sql_file(self):
        """Get SQL file from request (case-insensitive)"""
        for key in request.files:
            if key.lower() == 'sql_file':
                return request.files[key]
        return None

class TemplateList(Resource):
    def __init__(self):
        self.service = TemplateService()
    @tester_required
    def get(self):
        """Get list of available templates"""
        try:
            templates = self.service.list_templates()
            return APIResponse.success({
                "templates": templates,
                "count": len(templates)
            })
        except Exception as e:
            return APIResponse.server_error(f"Failed to fetch templates: {str(e)}")

class TemplateTableNames(Resource):
    def __init__(self):
        self.service = TemplateService()
    
    @tester_required
    def get(self, template_id):
        """Get only table names for a template"""
        try:
            result = self.service.get_table_names(template_id)
            return APIResponse.success(result)
        except ValueError as e:
            return APIResponse.not_found(str(e))
        except Exception as e:
            return APIResponse.server_error(f"Failed to get table names: {str(e)}")

class TemplateTableData(Resource):
    def __init__(self):
        self.service = TemplateService()
    
    @tester_required
    def get(self, template_id, table_names):
        """Get table data from template (supports single or multiple tables)"""
        try:
            # Parse table names (comma-separated)
            table_list = [t.strip() for t in table_names.split(',')]
            
            result = self.service.get_table_data(template_id, table_list)
            return APIResponse.success(result)
            
        except ValueError as e:
            return APIResponse.not_found(str(e))
        except Exception as e:
            return APIResponse.server_error(f"Failed to get table data: {str(e)}")

