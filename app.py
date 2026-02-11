import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta, timezone
import plotly.graph_objects as go

# 1. 페이지 설정 및 디자인 (기존 UI 유지)
st.set_page_config(page_title="Nostradamus V3.4 고도화", layout="wide")
st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { background-color: #05070a; }
    .metric-card { background: #10141c; border: 1px solid #1e2633; padding: 15px; border-radius: 8px; text-align: center; }
    .metric-value { color: #00f2ff !important; font-size: 1.8rem; font-weight: 800; }
    .miss-note { background: #b30000; padding: 18px; border-radius: 10px; color: white; }
    </style>
    """, unsafe_allow_html=True)

# 2. 고도화된 API 엔진 (V3.4 핵심)
@st.cache_data(ttl=3600)
def get_v3_4_engine():
    # [실제 구현 시 API 호출 로직 포함]
    # 미세먼지 가중치 계산 루틴
    pm_level = 95 # 에어코리아 API 결과값 가정
    thermal_limit_factor = 0.95 if pm_level > 80 else 1.0
    
    # 순부하 계산용 데이터셋
    times = [f"{i:02d}:00" for i in range(24)]
    total_load = np.array([65, 62, 60, 63, 68, 80, 88, 94, 98, 101, 105, 102, 98, 95, 96, 98, 102, 104, 102, 92, 85, 80, 75, 70])
    solar_gen = np.array([0, 0, 0, 0, 0, 0, 2, 8, 15, 18, 12, 10, 8, 7, 5, 2, 0, 0, 0, 0, 0, 0, 0, 0])
    net_load = total_load - solar_gen
    
    # 기울기(Slope) 분석: 가장 급격히 상승하는 시간대 도출
    slopes = np.diff(net_load, prepend=net_load[0])
    peak_slope_hour = np.argmax(slopes)
    
    return {
        "net_load": net_load,
        "total_load": total_load,
        "solar": solar_gen,
        "slopes": slopes,
        "peak_hour": peak_slope_hour,
        "limit": 105 * thermal_limit_factor
    }

data = get_v3_4_engine()

# 3. 상단 대시보드 (0전 2패 기록 반영)
st.title("🎯 Nostradamus V3.4 통합 관제 센터")
c1, c2, c3 = st.columns(3)
c1.markdown(f"<div class='metric-card'><div class='metric-label'>현재 순부하</div><div class='metric-value'>{data['net_load'][datetime.now().hour]} GW</div></div>", unsafe_allow_html=True)
c2.markdown(f"<div class='metric-card'><div class='metric-label'>예측 성공률</div><div class='metric-value' style='color:#ff3131 !important;'>0% (0전 2패)</div></div>", unsafe_allow_html=True)
c3.markdown(f"<div class='metric-card'><div class='metric-label'>발령 예상 시간</div><div class='metric-value'>{data['peak_hour']}:00</div></div>", unsafe_allow_html=True)

# 4. 고대비 그래프 (요구사항 반영: 네온 핑크, 하늘색, 투명 노랑)
fig = go.Figure()

# 태양광 영역 (투명도 있는 노랑)
fig.add_trace(go.Scatter(x=list(range(24)), y=data['solar'], fill='tozeroy', name='태양광(BTM)',
                         line=dict(color='rgba(255, 255, 0, 0.5)'), fillcolor='rgba(255, 255, 0, 0.2)'))
# 실제 총 부하 (네온 핑크 실선)
fig.add_trace(go.Scatter(x=list(range(24)), y=data['total_load'], name='실제 총 부하', 
                         line=dict(color='#FF1493', width=4)))
# 순부하 (하늘색)
fig.add_trace(go.Scatter(x=list(range(24)), y=data['net_load'], name='순부하(Net)', 
                         line=dict(color='#00BFFF', width=3)))
# 공급 한계선 (빨간 점선 + 라벨)
fig.add_hline(y=data['limit'], line_dash="dash", line_color="#FF3131", 
              annotation_text=f"공급 한계선 ({data['limit']:.1f}GW)", annotation_position="top right")

fig.update_layout(template="plotly_dark", 
                  xaxis=dict(title="시간", tickfont=dict(size=16)),
                  yaxis=dict(title="전력량 (GW)", tickfont=dict(size=16)))
st.plotly_chart(fig, use_container_width=True)

# 5. 오답노트 섹션
st.markdown(f"""
    <div class='miss-note'>
        <b>⚠️ [시스템 경고] 순부하 기울기 급증 감지</b><br>
        현재 {data['peak_hour']}:00 시점에 태양광 급감으로 인한 <b>순부하 기울기 {data['slopes'][data['peak_hour']]:.1f}</b> 도출. 
        미세먼지로 인한 화력제약(5%) 반영 시 예비율 위험 수준입니다.
    </div>
    """, unsafe_allow_html=True)
