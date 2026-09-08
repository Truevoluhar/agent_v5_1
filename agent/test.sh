TOKEN=eyJhbGciOiJSUzI1NiIsImtpZCI6Im9yYXgtT0FQcmFmMV9NQ0x4NjR0WHRoWXlhZ19sRkN2REsydGt1QVJMajAifQ.eyJhdWQiOlsiaHR0cHM6Ly9rdWJlcm5ldGVzLmRlZmF1bHQuc3ZjIl0sImV4cCI6MTgyMDQwMzM2MywiaWF0IjoxNzg4ODY3MzYzLCJpc3MiOiJodHRwczovL2t1YmVybmV0ZXMuZGVmYXVsdC5zdmMiLCJqdGkiOiIzOWUxOGM1Ny1kMTUwLTQ4NjEtOGIxOC03MTg3Nzg0YWQ4NWMiLCJrdWJlcm5ldGVzLmlvIjp7Im5hbWVzcGFjZSI6InRlc3QtcHJvamVjdC0xIiwic2VydmljZWFjY291bnQiOnsibmFtZSI6Im1vZGVsLWNsaWVudCIsInVpZCI6IjgzMjBkMGJmLTQxNDMtNDIwMi1iN2FmLTM3YWIyMDI0M2ZmOCJ9fSwibmJmIjoxNzg4ODY3MzYzLCJzdWIiOiJzeXN0ZW06c2VydmljZWFjY291bnQ6dGVzdC1wcm9qZWN0LTE6bW9kZWwtY2xpZW50In0.wkMhTMmXm72NAYkBDwWjxpU2MiMuk8ulc6uzwIzKMoFmyCm_Ov-cqnhFYSI2c8CkftTtPSrMquY3D88Ib_TeFmBGjecVDrRLk17uHDyq3hM_es39QRp3KerzsjlVCzzP2q7pW5mtgI2bAC5UvhtuLmW4lU0s2nKU-wP0Nf7WfBkiDqCMfJ9fRunM5R5RV26PCiuYjbH5KQdcqanuEVt6hjXvn0JiYiUi4bk1cVYMnrllSOVrUMhYkc4of60sgHZh_DPAsV4iEf_1rgLN910-BFOMk8RhEHjsriiZdUe5ZDbCd-9CTWlGOoSPsVPLMdJea_KbC4uqyAqFc-ih5j92Gg

echo $TOKEN | cut -d. -f2 | tr '_-' '/+' | base64 -d 2>/dev/null | jq .exp | xargs -I{} date -u -d @{}

curl -sk \
  https://redhataiqwen36-35b-a3b-test-project-1.apps.foswxai01.zpiz.si/v1/responses \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "redhataiqwen36-35b-a3b",
    "instructions": "Create a concise title. Return only the title.",
    "input": "hello",
    "temperature": 1.0,
    "max_output_tokens": 32500
  }'