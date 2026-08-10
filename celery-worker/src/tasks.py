from celery_app import app
import os
import time

@app.task(name='tasks.generate_certificate')
def generate_certificate(student_data: dict) -> dict:
    """
    結業證書生成任務
    業務情境:學員完成課程後,非同步產生含個人雷達圖的 PDF 結業證書

    student_data 範例:
    {
        "name": "小明",
        "scores": {"pwn": 85, "web": 90, "crypto": 70, "forensics": 80, "reverse": 75},
        "course": "AIS3 Junior 2026"
    }
    """
    # 模擬 PDF 產生耗時
    time.sleep(2)

    output_path = f"/tmp/cert_{student_data.get('name', 'unknown')}_{int(time.time())}.pdf"

    # 實際上只是模擬,不真的產生 PDF(避免 matplotlib 依賴讓 image 變大)
    with open(output_path, 'wb') as f:
        f.write(b'%PDF-1.4 (mock certificate)')

    return {
        "status": "success",
        "output": output_path,
        "student": student_data.get('name')
    }