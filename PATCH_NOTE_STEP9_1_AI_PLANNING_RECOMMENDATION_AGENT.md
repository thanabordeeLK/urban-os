# Patch: Step 9.1 AI Planning Recommendation Agent

เพิ่มระบบ AI Planning Recommendation Agent เพื่อสร้างข้อเสนอแนะเชิงผังเมืองจาก Candidate Ranking และ Evidence ของ Urban OS

## Menu ใหม่
เพิ่มเมนูใน Sidebar:

`🤖 AI Recommendation`

## ไฟล์ใหม่
- `components/ai_planning_recommendation.py`

## ไฟล์ที่แก้
- `app.py`
- `components/sidebar.py`
- `components/planning_report_generator.py`

## ความสามารถ
- อ่าน Candidate Ranking / Candidate Export
- อ่าน Suitability Summary และ Normalized Weights
- อ่าน UHI / Heat Risk Summary
- อ่าน Imported Layer / PostGIS metadata
- อ่าน Advanced Criteria Audit
- สร้าง Rule-Based Planning Recommendation ทันทีโดยไม่ต้องใช้ API
- ใช้ GPT Planning Agent ได้ถ้าตั้งค่า `OPENAI_API_KEY`
- Export CSV / Markdown / HTML / JSON
- ส่งผลเข้า Planning Report V2

## Output
- Suggested Land Use
- Development Phase
- Infrastructure Requirement
- Risk / Constraint Notes
- Planning Strategy
- Executive Summary
- GPT Planning Agent Report

## Workflow
1. Run Suitability Analysis
2. Generate Candidate Area Export
3. Run Candidate Ranking
4. ไปที่ AI Recommendation
5. ตรวจ Rule-Based Recommendation
6. ถ้ามี OPENAI_API_KEY ให้กด Generate GPT Planning Recommendation
7. Export Recommendation หรือรวมใน Planning Report

## Streamlit Secrets optional
ถ้าต้องการใช้ GPT Agent:

```toml
OPENAI_API_KEY = "your-key"
OPENAI_MODEL = "gpt-4.1-mini"
```

ถ้าไม่ตั้งค่า API key ระบบยังใช้ Rule-Based Recommendation ได้

## Commit message แนะนำ
`Add AI planning recommendation agent`