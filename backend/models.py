# Informal schema for reference
athlete_schema = {
    "athlete_id": str,
    "first_name": str,
    "last_name": str,
}

document_schema = {
    "document_id": str,
    "athlete_id": str,
    "file_path": str,
    "upload_date": str,
    "document_type": str,
    "text": str
}

user_schema = {
    "user_id": str,
    "username": str,
    "password": str
}

permission_schema = {
    "user_id": str,
    "athlete_id": str,
    "permission_level": str
}

medical_history_schema = {
    "history_id": str,
    "athlete_id": str,
}

physical_exam_schema = {
    "exam_id": str,
    "athlete_id": str,
}

shared_links_schema = {
    "link_id": str,
    "resource_type": str,
    "resource_id": str,
    "shared_by": str,
    "shared_with": str,
    "expires_at": str,
    "password": str
}