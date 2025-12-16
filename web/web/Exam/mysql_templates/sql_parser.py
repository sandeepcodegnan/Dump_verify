"""
SQL Parser - Single Responsibility (SoC)
Handles all SQL parsing operations
"""
import re

class SQLParser:
    def extract_table_names(self, sql_content):
        """Extract table names from CREATE TABLE statements"""
        pattern = r'CREATE\s+TABLE\s+([\w_]+)\s*\('
        return re.findall(pattern, sql_content, re.IGNORECASE)
    
    def parse_table(self, sql_content, table_name):
        """Parse specific table schema and data"""
        result = {
            "schema": [],
            "data": [],
            "raw_sql": ""
        }
        
        # Parse CREATE TABLE
        self._parse_create_table(sql_content, table_name, result)
        
        # Parse INSERT data
        self._parse_insert_data(sql_content, table_name, result)
        
        return result
    
    def _parse_create_table(self, sql_content, table_name, result):
        """Parse CREATE TABLE statement"""
        create_pattern = rf'CREATE TABLE {table_name}\s*\((.*?)\);'
        create_match = re.search(create_pattern, sql_content, re.DOTALL | re.IGNORECASE)
        
        if not create_match:
            return
        
        columns_def = create_match.group(1)
        lines = self._split_column_definitions(columns_def)
        
        for line in lines:
            line = line.strip()
            if not line or 'FOREIGN KEY' in line.upper():
                continue
            
            column_info = self._parse_column_definition(line)
            if column_info:
                result["schema"].append(column_info)
        
        result["raw_sql"] += create_match.group(0) + ";\n\n"
    
    def _parse_insert_data(self, sql_content, table_name, result):
        """Parse INSERT statements"""
        insert_pattern = rf'INSERT INTO {table_name}.*?VALUES\s*(.*?);'
        insert_match = re.search(insert_pattern, sql_content, re.DOTALL | re.IGNORECASE)
        
        if not insert_match:
            return
        
        values_part = insert_match.group(1)
        value_groups = re.findall(r'\((.*?)\)', values_part)
        
        for group in value_groups:
            values = self._parse_values(group)
            result["data"].append(values)
        
        result["raw_sql"] += insert_match.group(0)
    
    def _split_column_definitions(self, columns_def):
        """Split column definitions handling nested parentheses"""
        lines = []
        current_line = ""
        paren_count = 0
        
        for char in columns_def:
            if char == '(':
                paren_count += 1
            elif char == ')':
                paren_count -= 1
            elif char == ',' and paren_count == 0:
                lines.append(current_line.strip())
                current_line = ""
                continue
            current_line += char
        
        if current_line.strip():
            lines.append(current_line.strip())
        
        return lines
    
    def _parse_column_definition(self, line):
        """Parse individual column definition"""
        if 'PRIMARY KEY' in line.upper():
            parts = line.split()
            return {
                "name": parts[0],
                "type": parts[1],
                "constraints": 'PRIMARY KEY'
            }
        else:
            parts = line.split(None, 2)
            if len(parts) >= 2:
                return {
                    "name": parts[0],
                    "type": parts[1],
                    "constraints": parts[2] if len(parts) > 2 else ''
                }
        return None
    
    def _parse_values(self, group):
        """Parse VALUES clause"""
        values = []
        current_val = ""
        in_quotes = False
        quote_char = None
        
        for char in group:
            if char in ["'", '"'] and not in_quotes:
                in_quotes = True
                quote_char = char
            elif char == quote_char and in_quotes:
                in_quotes = False
                quote_char = None
            elif char == ',' and not in_quotes:
                values.append(current_val.strip().strip("'\""))
                current_val = ""
                continue
            current_val += char
        
        if current_val.strip():
            values.append(current_val.strip().strip("'\""))
        
        return values