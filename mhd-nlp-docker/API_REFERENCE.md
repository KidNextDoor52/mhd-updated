# 📡 API Reference

## Auth
- `POST /signup`
  - body: `username, password`
- `POST /token`
  - OAuth2 password grant
  - returns `{access_token, token_type}`

## Dashboard
- `GET /dashboard?tag=&date=`
  - returns filtered docs

## Forms
- `POST /form/create`
  - body: `{name, age, injury_history, status}`
- `GET /form/create`
  - returns HTML form

## Share Links
- `POST /share`
  - form-data: `{resource_id, resource_type, expires_in, password?, shared_with?}`
- `GET /shared/{link_id}`
  - verify + show resource

