"""
Progress Service
Optimized business logic for intern progress reporting
"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from .base_service import BaseService
from web.Exam.Testing.utils.formatters import format_tags
from web.Exam.Testing.exceptions.testing_exceptions import ValidationError

class ProgressService(BaseService):
    """Service for progress reporting with optimized queries"""
    
    LOCAL_TZ = ZoneInfo("Asia/Kolkata")
    PLACEHOLDER = "N/A"
    
    def _parse_date_range(self, date_str: str) -> tuple:
        """Parse date filter and return UTC range"""
        try:
            local_date = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=self.LOCAL_TZ)
            start_utc = local_date.astimezone(ZoneInfo("UTC"))
            end_utc = start_utc + timedelta(days=1)
            return start_utc, end_utc
        except ValueError:
            raise ValidationError("Invalid date format. Use YYYY-MM-DD")
    

    
    def _get_dump_data(self, date_range: Optional[tuple]) -> List[Dict]:
        """Get dump data with type classification"""
        query = {}
        if date_range:
            start_utc, end_utc = date_range
            query["date"] = {"$gte": start_utc, "$lt": end_utc}
        
        dumps = self.find_many(
            "internsdumped",
            query,
            {"internId": 1, "subject": 1, "tags": 1, "date": 1, "questionId": 1}
        )
        
        # Get question types for classification
        question_types = self._get_question_types([d.get("questionId") for d in dumps])
        
        # Aggregate dump statistics
        dump_stats = {}
        for dump in dumps:
            key = self._build_dump_key(dump)
            if key not in dump_stats:
                dump_stats[key] = self._init_dump_stats(dump)
            
            # Classify by question type
            question_type = question_types.get(str(dump.get("questionId", "")), "mcq_test")
            self._increment_dump_count(dump_stats[key], question_type)
        
        return list(dump_stats.values())
    
    def _get_question_types(self, question_ids: List[str]) -> Dict:
        """Get question types for classification"""
        from bson import ObjectId
        
        valid_ids = []
        for qid in question_ids:
            try:
                if qid:
                    valid_ids.append(ObjectId(qid))
            except Exception:
                continue
        
        if not valid_ids:
            return {}
        
        verifications = self.find_many(
            self.collections["verification"],
            {"questionId": {"$in": valid_ids}},
            {"questionId": 1, "questionType": 1}
        )
        
        return {str(v["questionId"]): v["questionType"] for v in verifications}
    
    def _build_dump_key(self, dump: Dict) -> tuple:
        """Build key for dump aggregation"""
        intern_id = dump["internId"]
        subject = dump["subject"].lower()
        tags = format_tags(dump.get("tags", []))
        date = self._to_local_day(dump["date"])
        return (intern_id, subject, tuple(tags), date)
    
    def _init_dump_stats(self, dump: Dict) -> Dict:
        """Initialize dump statistics structure"""
        intern_id, subject, tags, date = self._build_dump_key(dump)
        return {
            "internId": intern_id,
            "subject": subject,
            "tag": list(tags),
            "date": date,
            "mcq_created": 0, "code_created": 0, "code_codeplayground_created": 0, "query_created": 0, "query_codeplayground_created": 0,
            "mcq_verified": 0, "code_verified": 0, "code_codeplayground_verified": 0, "query_verified": 0, "query_codeplayground_verified": 0,
            "mcq_dumped": 0, "code_dumped": 0, "code_codeplayground_dumped": 0, "query_dumped": 0, "query_codeplayground_dumped": 0
        }
    
    def _increment_dump_count(self, stats: Dict, question_type: str) -> None:
        """Increment dump count using mapping"""
        type_mapping = {
            "mcq_test": "mcq_dumped",
            "code_test": "code_dumped", 
            "code_codeplayground_test": "code_codeplayground_dumped",
            "query_test": "query_dumped",
            "query_codeplayground_test": "query_codeplayground_dumped"
        }
        field = type_mapping.get(question_type, "mcq_dumped")
        stats[field] += 1 

    

    
    def _get_tester_info(self) -> Dict:
        """Get tester information"""
        testers = self.find_many(
            self.collections["testers"],
            {},
            {"id": 1, "name": 1, "email": 1}
        )
        return {t["id"]: t for t in testers}
    
    def _to_local_day(self, utc_datetime: datetime) -> str:
        """Convert UTC datetime to local day string"""
        if utc_datetime.tzinfo is None:
            utc_datetime = utc_datetime.replace(tzinfo=ZoneInfo("UTC"))
        local_dt = utc_datetime.astimezone(self.LOCAL_TZ)
        return local_dt.strftime("%Y-%m-%d")
    
    def get_testers_overall(self, date: str) -> Dict:
        """API 1: Get all testers with overall aggregated stats"""
        try:
            date_range = self._parse_date_range(date)
            start_utc, end_utc = date_range
            
            # Get all testers
            testers = self.find_many(
                self.collections["testers"],
                {},
                {"id": 1, "name": 1, "email": 1}
            )
            
            # Get aggregated stats for all testers with date filter
            pipeline = [
                {"$match": {"createdAt": {"$gte": start_utc, "$lt": end_utc}}},
                {"$group": {
                    "_id": "$id",
                    "total_created": {"$sum": 1},
                    "total_verified": {"$sum": {"$cond": [{"$eq": ["$verified", True]}, 1, 0]}}
                }}
            ]
            
            verification_stats = list(self.db[self.collections["verification"]].aggregate(pipeline))
            
            # Get dump stats with date filter
            dump_pipeline = [
                {"$match": {"date": {"$gte": start_utc, "$lt": end_utc}}},
                {"$group": {
                    "_id": "$internId",
                    "total_dumped": {"$sum": 1}
                }}
            ]
            
            dump_stats = list(self.db["internsdumped"].aggregate(dump_pipeline))
            
            # Merge data and calculate overall totals
            result = []
            overall_created = 0
            overall_verified = 0
            overall_dumped = 0
            
            for tester in testers:
                intern_id = tester["id"]
                
                # Find stats
                v_stat = next((s for s in verification_stats if s["_id"] == intern_id), {})
                d_stat = next((s for s in dump_stats if s["_id"] == intern_id), {})
                
                created = v_stat.get("total_created", 0)
                verified = v_stat.get("total_verified", 0)
                dumped = d_stat.get("total_dumped", 0)
                
                result.append({
                    "name": tester["name"],
                    "internId": intern_id
                })
                
                # Add to overall totals
                overall_created += created
                overall_verified += verified
                overall_dumped += dumped
            
            return {
                "success": True, 
                "testers": result,
                "overall_total_created": overall_created,
                "overall_total_verified": overall_verified,
                "overall_total_dumped": overall_dumped
            }
        except Exception as e:
            return {"success": False, "message": str(e)}
    
    def get_tester_by_id(self, intern_id: str, date: str) -> Dict:
        """API 2: Get tester by internId with subjects and stats"""
        try:
            date_range = self._parse_date_range(date)
            start_utc, end_utc = date_range
            
            # Get tester info
            tester = self.find_one(
                self.collections["testers"],
                {"id": intern_id},
                {"name": 1, "email": 1}
            )
            
            if not tester:
                return {"success": False, "message": "Tester not found"}
            
            # Get subjects and stats with date filter
            pipeline = [
                {"$match": {"id": intern_id, "createdAt": {"$gte": start_utc, "$lt": end_utc}}},
                {"$group": {
                    "_id": "$subject",
                    "total_created": {"$sum": 1},
                    "total_verified": {"$sum": {"$cond": [{"$eq": ["$verified", True]}, 1, 0]}}
                }}
            ]
            
            verification_stats = list(self.db[self.collections["verification"]].aggregate(pipeline))
            
            # Get dump stats by subject with date filter
            dump_pipeline = [
                {"$match": {"internId": intern_id, "date": {"$gte": start_utc, "$lt": end_utc}}},
                {"$group": {
                    "_id": "$subject",
                    "total_dumped": {"$sum": 1}
                }}
            ]
            
            dump_stats = list(self.db["internsdumped"].aggregate(dump_pipeline))
            
            # Merge subject data
            subjects = []
            all_subjects = set([s["_id"] for s in verification_stats] + [s["_id"] for s in dump_stats])
            
            for subject in all_subjects:
                v_stat = next((s for s in verification_stats if s["_id"] == subject), {})
                d_stat = next((s for s in dump_stats if s["_id"] == subject), {})
                
                subjects.append({
                    "subject": subject,
                    "total_created": v_stat.get("total_created", 0),
                    "total_verified": v_stat.get("total_verified", 0),
                    "total_dumped": d_stat.get("total_dumped", 0)
                })
            
            # Calculate overall totals
            overall_created = sum(s["total_created"] for s in subjects)
            overall_verified = sum(s["total_verified"] for s in subjects)
            overall_dumped = sum(s["total_dumped"] for s in subjects)
            
            return {
                "success": True,
                "tester": {
                    "name": tester["name"],
                    "internId": intern_id,
                    "subjects": subjects,
                    "total_created": overall_created,
                    "total_verified": overall_verified,
                    "total_dumped": overall_dumped
                }
            }
        except Exception as e:
            return {"success": False, "message": str(e)}
    
    def get_tester_subject_details(self, intern_id: str, subject: str, date: str) -> Dict:
        """API 3: Get detailed subject-based data for a tester"""
        try:
            date_range = self._parse_date_range(date)
            start_utc, end_utc = date_range
            
            # Get tester info
            tester = self.find_one(
                self.collections["testers"],
                {"id": intern_id},
                {"name": 1, "email": 1}
            )
            
            if not tester:
                return {"success": False, "message": "Tester not found"}
            
            # Get verification data for this tester and subject with date filter
            verification_data = self.find_many(
                self.collections["verification"],
                {"id": intern_id, "subject": {"$regex": f"^{subject}$", "$options": "i"}, "createdAt": {"$gte": start_utc, "$lt": end_utc}}
            )
            
            # Get dump data with date filter
            dump_data = self.find_many(
                "internsdumped",
                {"internId": intern_id, "subject": {"$regex": f"^{subject}$", "$options": "i"}, "date": {"$gte": start_utc, "$lt": end_utc}}
            )
            
            # Process data by date and tag
            stats = {}
            type_mapping = {
                "mcq_test": "mcq",
                "code_test": "code",
                "code_codeplayground_test": "code_codeplayground",
                "query_test": "query",
                "query_codeplayground_test": "query_codeplayground"
            }
            
            # Process verification records
            for record in verification_data:
                tag = str(record.get("tag", "")).strip().lower()
                question_type = record.get("questionType", "")
                verified = record.get("verified", False)
                
                # Process creation
                if record.get("createdAt"):
                    date = self._to_local_day(record["createdAt"])
                    key = (date, tag)
                    
                    if key not in stats:
                        stats[key] = self._init_detailed_stats(tester, intern_id, subject, tag, date)
                    
                    q_type = type_mapping.get(question_type, "mcq")
                    stats[key][f"{q_type}_created"] += 1
                
                # Process verification
                if verified and (record.get("verifiedAt") or record.get("timestamp")):
                    verify_date = record.get("verifiedAt") or record.get("timestamp")
                    date = self._to_local_day(verify_date)
                    key = (date, tag)
                    
                    if key not in stats:
                        stats[key] = self._init_detailed_stats(tester, intern_id, subject, tag, date)
                    
                    q_type = type_mapping.get(question_type, "mcq")
                    stats[key][f"{q_type}_verified"] += 1
            
            # Process dump records
            question_types = self._get_question_types([d.get("questionId") for d in dump_data])
            
            for dump in dump_data:
                tags = format_tags(dump.get("tags", []))
                date = self._to_local_day(dump["date"])
                
                for tag in tags:
                    key = (date, tag.lower())
                    
                    if key not in stats:
                        stats[key] = self._init_detailed_stats(tester, intern_id, subject, tag, date)
                    
                    question_type = question_types.get(str(dump.get("questionId", "")), "mcq_test")
                    dump_field = {
                        "mcq_test": "mcq_dumped",
                        "code_test": "code_dumped",
                        "code_codeplayground_test": "code_codeplayground_dumped",
                        "query_test": "query_dumped",
                        "query_codeplayground_test": "query_codeplayground_dumped"
                    }.get(question_type, "mcq_dumped")
                    
                    stats[key][dump_field] += 1
            
            # Format results
            results = []
            for i, ((date, tag), stat) in enumerate(sorted(stats.items()), 1):
                stat["S/No"] = f"{i:03d}"
                
                # Calculate totals only for existing fields
                total_created = sum(stat.get(f"{t}_created", 0) for t in ["mcq", "code", "code_codeplayground", "query", "query_codeplayground"])
                total_verified = sum(stat.get(f"{t}_verified", 0) for t in ["mcq", "code", "code_codeplayground", "query", "query_codeplayground"])
                total_dumped = sum(stat.get(f"{t}_dumped", 0) for t in ["mcq", "code", "code_codeplayground", "query", "query_codeplayground"])
                
                stat["total_created"] = total_created
                stat["total_verified"] = total_verified
                stat["total_dumped"] = total_dumped
                results.append(stat)
            
            return {"success": True, "progress": results}
        except Exception as e:
            return {"success": False, "message": str(e)}
    
    def _init_detailed_stats(self, tester: Dict, intern_id: str, subject: str, tag: str, date: str) -> Dict:
        """Initialize detailed statistics structure based on subject"""
        from web.Exam.Testing.config.testing_config import get_subject_question_types
        
        allowed_types = get_subject_question_types(subject)
        stats = {
            "name": tester["name"],
            "email": tester["email"],
            "internId": intern_id,
            "subject": subject.title(),
            "tag": tag,
            "date": date
        }
        
        # Only add fields for allowed question types
        for q_type in ["mcq", "code", "code_codeplayground", "query", "query_codeplayground"]:
            if q_type in allowed_types:
                stats[f"{q_type}_created"] = 0
                stats[f"{q_type}_verified"] = 0
                stats[f"{q_type}_dumped"] = 0
        
        return stats