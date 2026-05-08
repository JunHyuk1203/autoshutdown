import urllib.request
import urllib.parse
import json

school_name = "서울과학고등학교"
url = f"https://open.neis.go.kr/hub/schoolInfo?Type=json&pIndex=1&pSize=10&SCHUL_NM={urllib.parse.quote(school_name)}"

req = urllib.request.Request(url)
with urllib.request.urlopen(req) as response:
    data = json.loads(response.read().decode('utf-8'))
    print(json.dumps(data, indent=2, ensure_ascii=False))

if "schoolInfo" in data:
    row = data["schoolInfo"][1]["row"][0]
    office_code = row["ATPT_OFCDC_SC_CODE"]
    school_code = row["SD_SCHUL_CODE"]
    school_kind = row["SCHUL_KND_SC_NM"]
    
    print(office_code, school_code, school_kind)
    
    # Test high school timetable
    timetable_url = f"https://open.neis.go.kr/hub/hisTimetable?Type=json&ATPT_OFCDC_SC_CODE={office_code}&SD_SCHUL_CODE={school_code}&GRADE=1&CLASS_NM=1&TI_FROM_YMD=20260504&TI_TO_YMD=20260508"
    req = urllib.request.Request(timetable_url)
    try:
        with urllib.request.urlopen(req) as res:
            td = json.loads(res.read().decode('utf-8'))
            print(json.dumps(td, indent=2, ensure_ascii=False))
    except Exception as e:
        print(e)
