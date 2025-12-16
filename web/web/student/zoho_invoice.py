from flask import request
from flask_restful import Resource

from web.db.db_utils import get_collection

collection = get_collection('students')

class zoho_Invoice(Resource):
    def __init__(self):
        super().__init__()
        self.collection = collection

    def put(self):
        data = request.json
        stdid = data.get("studentId")
        zohoId = data.get("zohoId")

        # if not stdid and zohoId :
        #     return {"message":"Missing required fields"},400
        
        student = self.collection.find_one({"$or":[{ "zohoID":zohoId },{ "studentId": stdid } ]})
        if not student:
            return {"message": "Student not found"}, 404

        updated_data = {
            "created_time":data.get("Invmodif_T"),
            "invoiceURL": data.get("invoiceURL"),
            "total":data.get("totalFee"),
            "paidamount":data.get("paidAmount"),
            "balance":data.get("balance"),
            "duedate":data.get("dueDate")
        }
        self.collection.update_one({"$or":[{ "studentId": stdid },{ "zohoID":zohoId }]},{"$set": updated_data})

        return {"message": "Student deatils updated successfully", "studentId": stdid}, 200