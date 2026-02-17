# Testing Notes

No automated tests are present in this repo yet.

Minimal sanity check (manual):
1. Start the backend: `python -m backend.app`
2. Fetch inbound data: `curl http://localhost:5000/api/inbound | python -m json.tool`
3. Verify the response contains `next_at_42` (max 2) and `in_flight` (max 8) and that Fulton ETA is blank when the train is past Fulton.

If GTFS data is unavailable, set `MTA_API_KEY` if required and try again.
