import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ────────────────────────────────────────────────
#  설정
# ────────────────────────────────────────────────
st.set_page_config(
    page_title="수열 학습 RPG",
    page_icon="🎮",
    layout="wide"
)

# ────────────────────────────────────────────────
#  RPG 시스템 설정
# ────────────────────────────────────────────────
TOTAL_LESSONS = 19
NO_MENTOR = "멘토 없음 / 혼자 풀었음"

ALL_STUDENTS = {
    "2학년 5반": ["곽민석","김다율","김제니아","백종우","이시원",
                  "조건희","최민준","최은호","김서진","김채은",
                  "김하윤","남수정","박찬비","양은서","이수연",
                  "전유영","정민경","조은서","홍기담"],
    "2학년 6반": ["김채민","양수현","양준환","여민겸","윤영민",
                  "이도윤","전재훈","전진우","김예원","김유주",
                  "류효연","송민경","안혜준","안효은","이다인",
                  "이연서","이예은","전하은","정연아"]
}

LEVEL_TABLE = [
    (0,  2,  1, "🌱", "수학 새싹",     "EF9A9A"),
    (3,  5,  2, "📚", "성실한 학습자", "FFB74D"),
    (6,  9,  3, "⚔️", "베테랑 수학자", "FFF176"),
    (10, 14, 4, "🌟", "수열 마스터",   "81C784"),
    (15, 19, 5, "👑", "전설의 수학왕", "64B5F6"),
]

def get_level_info(count):
    for mn, mx, lv, icon, title, color in LEVEL_TABLE:
        if mn <= count <= mx:
            xp_in_level = count - mn
            xp_needed   = mx - mn + 1
            return lv, icon, title, color, xp_in_level, xp_needed
    lv, icon, title, color = 5, "👑", "전설의 수학왕", "64B5F6"
    return lv, icon, title, color, TOTAL_LESSONS, TOTAL_LESSONS

# ────────────────────────────────────────────────
#  CSS
# ────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;600;700;900&display=swap');

html, body, [class*="css"] {
    font-family: 'Noto Sans KR', sans-serif;
}

/* 배경 */
.stApp { background: #0F0F1A; }
[data-testid="stSidebar"] { background: #16162A; border-right: 1px solid #2A2A4A; }

/* 헤더 타이틀 */
.rpg-header {
    text-align: center;
    padding: 1.5rem 0 0.5rem;
}
.rpg-header h1 {
    font-size: 2.4rem;
    font-weight: 900;
    background: linear-gradient(135deg, #A78BFA, #60A5FA, #34D399);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin: 0;
    letter-spacing: -0.5px;
}
.rpg-header p {
    color: #6B7280;
    font-size: 0.85rem;
    margin: 0.3rem 0 0;
}

/* 탭 */
[data-testid="stTabs"] button {
    color: #6B7280 !important;
    font-weight: 600;
    font-size: 0.9rem;
}
[data-testid="stTabs"] button[aria-selected="true"] {
    color: #A78BFA !important;
    border-bottom-color: #A78BFA !important;
}

/* 메트릭 카드 */
.metric-card {
    background: #16162A;
    border: 1px solid #2A2A4A;
    border-radius: 12px;
    padding: 1rem 1.2rem;
    text-align: center;
}
.metric-card .val {
    font-size: 2rem;
    font-weight: 900;
    color: #E0E7FF;
}
.metric-card .lbl {
    font-size: 0.75rem;
    color: #6B7280;
    margin-top: 0.2rem;
}

/* 플레이어 카드 */
.player-card {
    background: #16162A;
    border: 1px solid #2A2A4A;
    border-radius: 14px;
    padding: 1rem 1.1rem;
    margin-bottom: 0.6rem;
    transition: border-color 0.2s;
}
.player-card:hover { border-color: #4C4CA0; }
.player-card .name-row {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.45rem;
}
.player-card .rank {
    font-size: 0.8rem;
    color: #6B7280;
    min-width: 1.5rem;
}
.player-card .icon { font-size: 1.1rem; }
.player-card .name {
    font-size: 0.95rem;
    font-weight: 700;
    color: #E0E7FF;
    flex: 1;
}
.player-card .lv-badge {
    font-size: 0.72rem;
    font-weight: 700;
    padding: 0.15rem 0.5rem;
    border-radius: 20px;
    background: #1E1E3A;
    color: #A78BFA;
    border: 1px solid #3B3B6A;
}
.player-card .title-text {
    font-size: 0.72rem;
    color: #6B7280;
    margin-bottom: 0.4rem;
    padding-left: 1.9rem;
}

/* XP 바 */
.xp-bar-wrap {
    background: #0F0F1A;
    border-radius: 6px;
    height: 8px;
    overflow: hidden;
    margin: 0.1rem 0 0.3rem;
}
.xp-bar-fill {
    height: 100%;
    border-radius: 6px;
    transition: width 0.5s ease;
}
.xp-label {
    display: flex;
    justify-content: space-between;
    font-size: 0.68rem;
    color: #4B5563;
}

/* 반 카드 */
.class-card {
    background: #16162A;
    border: 1px solid #2A2A4A;
    border-radius: 14px;
    padding: 1.2rem 1.4rem;
}
.class-card h3 {
    font-size: 1rem;
    font-weight: 700;
    color: #E0E7FF;
    margin: 0 0 0.8rem;
}

/* 멘토 카드 */
.mentor-card {
    background: #16162A;
    border: 1px solid #2A2A4A;
    border-radius: 12px;
    padding: 0.8rem 1rem;
    margin-bottom: 0.5rem;
    display: flex;
    align-items: center;
    gap: 0.8rem;
}
.mentor-card .m-rank {
    font-size: 1.2rem;
    min-width: 2rem;
    text-align: center;
}
.mentor-card .m-info { flex: 1; }
.mentor-card .m-name {
    font-size: 0.9rem;
    font-weight: 700;
    color: #E0E7FF;
}
.mentor-card .m-score {
    font-size: 0.8rem;
    color: #A78BFA;
    font-weight: 700;
}

/* 알림 배너 */
.warn-box {
    background: #1A1A0F;
    border: 1px solid #3D3A00;
    border-radius: 10px;
    padding: 0.7rem 1rem;
    color: #FCD34D;
    font-size: 0.82rem;
    margin-bottom: 1rem;
}

div[data-testid="stVerticalBlock"] { gap: 0 !important; }
</style>
""", unsafe_allow_html=True)

# ────────────────────────────────────────────────
#  구글 시트 연결
# ────────────────────────────────────────────────
@st.cache_resource
def get_gc():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        st.secrets["gcp_service_account"], scope
    )
    return gspread.authorize(creds)

@st.cache_data(ttl=300)
def load_all_responses():
    gc = get_gc()
    try:
        sh = gc.open("수열_폼_응답_통합")
    except Exception:
        return pd.DataFrame()

    all_dfs = []
    for ws in sh.worksheets():
        try:
            raw = ws.get_all_values()
            if len(raw) < 2:
                continue
            headers = raw[0]
            seen = {}
            clean = []
            for h in headers:
                seen[h] = seen.get(h, 0) + 1
                clean.append(h if seen[h] == 1 else f"{h}_{seen[h]}")

            df = pd.DataFrame(raw[1:], columns=clean)
            df = df[df.iloc[:, 0] != ""].copy()
            if df.empty:
                continue

            tab = ws.title
            df["차시"] = tab.split("_", 1)[1] if "_" in tab and not tab.startswith("Form") else tab

            for base in ["본인 이름", "도움 준 멘토 이름"]:
                dup = base + "_2"
                if base in df.columns and dup in df.columns:
                    df[base] = df[base].replace("", pd.NA).fillna(df[dup])
                    df.drop(columns=[dup], inplace=True)
                elif dup in df.columns:
                    df.rename(columns={dup: base}, inplace=True)

            ts = clean[0]
            df.rename(columns={ts: "타임스탬프"}, inplace=True)
            df["타임스탬프"] = pd.to_datetime(df["타임스탬프"], errors="coerce")
            all_dfs.append(df)
        except Exception:
            continue

    return pd.concat(all_dfs, ignore_index=True) if all_dfs else pd.DataFrame()

# ────────────────────────────────────────────────
#  헬퍼
# ────────────────────────────────────────────────
def xp_bar_html(count, color_hex):
    lv, icon, title, color, xp_in, xp_need = get_level_info(count)
    pct = min(int(xp_in / xp_need * 100), 100)
    return f"""
    <div class="xp-bar-wrap">
        <div class="xp-bar-fill" style="width:{pct}%;background:#{color_hex};"></div>
    </div>
    <div class="xp-label">
        <span>{xp_in}/{xp_need} XP</span>
        <span>다음 레벨까지 {xp_need - xp_in} XP</span>
    </div>
    """

def medal(rank):
    return ["🥇","🥈","🥉"][rank] if rank < 3 else f"{rank+1}위"

# ────────────────────────────────────────────────
#  헤더
# ────────────────────────────────────────────────
st.markdown("""
<div class="rpg-header">
    <h1>🎮 수열 학습 RPG 대시보드</h1>
    <p>대동세무고등학교 · 대수 | 데이터는 5분마다 자동 갱신됩니다</p>
</div>
""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ────────────────────────────────────────────────
#  사이드바
# ────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🔍 필터")
    class_filter = st.multiselect(
        "반 선택",
        options=list(ALL_STUDENTS.keys()),
        default=list(ALL_STUDENTS.keys())
    )
    if st.button("🔄 새로고침"):
        st.cache_data.clear()
        st.rerun()

    st.divider()
    st.markdown("### 🏆 레벨 가이드")
    for mn, mx, lv, icon, title, color in LEVEL_TABLE:
        st.markdown(
            f'<div style="font-size:0.8rem;color:#9CA3AF;padding:0.2rem 0">'
            f'{icon} <b style="color:#E0E7FF">Lv.{lv}</b> {title}<br>'
            f'<span style="color:#4B5563;font-size:0.7rem">{mn}~{mx}차시 제출</span></div>',
            unsafe_allow_html=True
        )

# ────────────────────────────────────────────────
#  데이터 로드
# ────────────────────────────────────────────────
df = load_all_responses()

if df.empty:
    st.markdown('<div class="warn-box">⚠️ 아직 응답 데이터가 없거나 시트 연결을 확인해주세요.</div>', unsafe_allow_html=True)
    st.stop()

if "반" in df.columns and class_filter:
    df_f = df[df["반"].isin(class_filter)].copy()
else:
    df_f = df.copy()

all_lessons = sorted(df_f["차시"].unique().tolist()) if "차시" in df_f.columns else []

# ────────────────────────────────────────────────
#  상단 요약 지표
# ────────────────────────────────────────────────
total_students = sum(len(v) for k, v in ALL_STUDENTS.items() if k in class_filter)
submitted_names = df_f["본인 이름"].nunique() if "본인 이름" in df_f.columns else 0
total_responses = len(df_f)
mentor_col = next((c for c in ["도움 준 멘토 이름","멘토 이름"] if c in df_f.columns), None)
mentor_count = int(df_f[mentor_col].notna().sum()) if mentor_col else 0

c1, c2, c3, c4 = st.columns(4)
for col, val, lbl in [
    (c1, total_responses, "총 제출 수"),
    (c2, f"{submitted_names}/{total_students}", "참여 학생"),
    (c3, len(all_lessons), "진행 차시"),
    (c4, mentor_count, "멘토 지목 수"),
]:
    col.markdown(f"""
    <div class="metric-card">
        <div class="val">{val}</div>
        <div class="lbl">{lbl}</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ────────────────────────────────────────────────
#  탭
# ────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "🗺️ 전체 현황",
    "⚔️ 개인 레벨",
    "👑 멘토 랭킹",
    "🏰 반별 현황",
])

# ══════════════════════════════════════════════
#  탭 1: 전체 현황
# ══════════════════════════════════════════════
with tab1:
    st.markdown("#### 📊 차시별 제출 현황")

    if "차시" in df_f.columns:
        lesson_counts = (
            df_f.groupby("차시").size()
            .reset_index(name="제출 수")
            .sort_values("차시")
        )
        fig = px.bar(
            lesson_counts, x="차시", y="제출 수",
            color="제출 수",
            color_continuous_scale=[[0,"#2D1B69"],[0.5,"#7C3AED"],[1,"#A78BFA"]],
            text="제출 수",
        )
        fig.update_traces(textposition="outside", marker_line_width=0)
        fig.update_layout(
            paper_bgcolor="#0F0F1A", plot_bgcolor="#0F0F1A",
            font_color="#9CA3AF",
            xaxis=dict(tickangle=-45, gridcolor="#1E1E3A", tickfont_color="#6B7280"),
            yaxis=dict(gridcolor="#1E1E3A", tickfont_color="#6B7280"),
            coloraxis_showscale=False,
            height=340, margin=dict(t=20, b=60),
        )
        st.plotly_chart(fig, use_container_width=True)

    # 레벨 분포
    if "본인 이름" in df_f.columns:
        st.markdown("#### 🎮 레벨 분포 현황")
        student_counts = df_f.groupby("본인 이름")["차시"].nunique()
        level_dist = {f"Lv.{lv} {icon} {title}": 0 for _, _, lv, icon, title, _ in LEVEL_TABLE}
        for name, cnt in student_counts.items():
            lv, icon, title, *_ = get_level_info(cnt)
            key = f"Lv.{lv} {icon} {title}"
            level_dist[key] = level_dist.get(key, 0) + 1

        cols = st.columns(5)
        for i, (mn, mx, lv, icon, title, color) in enumerate(LEVEL_TABLE):
            key = f"Lv.{lv} {icon} {title}"
            cnt = level_dist.get(key, 0)
            cols[i].markdown(f"""
            <div class="metric-card">
                <div style="font-size:1.8rem">{icon}</div>
                <div class="val" style="font-size:1.5rem;color:#{color}">{cnt}명</div>
                <div class="lbl">Lv.{lv} {title}</div>
            </div>
            """, unsafe_allow_html=True)

# ══════════════════════════════════════════════
#  탭 2: 개인 레벨
# ══════════════════════════════════════════════
with tab2:
    if "본인 이름" not in df_f.columns or "차시" not in df_f.columns:
        st.info("본인 이름 데이터를 찾을 수 없습니다.")
    else:
        for class_name in ALL_STUDENTS:
            if class_name not in class_filter:
                continue

            st.markdown(f"#### {class_name}")
            students = ALL_STUDENTS[class_name]
            class_df = df_f[df_f["반"] == class_name] if "반" in df_f.columns else df_f

            # 각 학생 제출 수 계산
            student_data = []
            for name in students:
                s_df = class_df[class_df["본인 이름"] == name]
                cnt = s_df["차시"].nunique()
                lv, icon, title, color, xp_in, xp_need = get_level_info(cnt)
                student_data.append((name, cnt, lv, icon, title, color, xp_in, xp_need))

            # 레벨 높은 순 정렬
            student_data.sort(key=lambda x: (-x[2], -x[1]))

            col_a, col_b = st.columns(2)
            for i, (name, cnt, lv, icon, title, color, xp_in, xp_need) in enumerate(student_data):
                pct = min(int(xp_in / xp_need * 100), 100)
                is_max = cnt == TOTAL_LESSONS

                card_html = f"""
                <div class="player-card" style="{'border-color:#F59E0B' if is_max else ''}">
                    <div class="name-row">
                        <span class="rank">{medal(i)}</span>
                        <span class="icon">{icon}</span>
                        <span class="name">{name}</span>
                        <span class="lv-badge">Lv.{lv}</span>
                    </div>
                    <div class="title-text">{title} · {cnt}/{TOTAL_LESSONS} 차시</div>
                    <div class="xp-bar-wrap">
                        <div class="xp-bar-fill" style="width:{pct}%;background:#{color};"></div>
                    </div>
                    <div class="xp-label">
                        <span>{xp_in}/{xp_need} XP</span>
                        <span>{'✨ MAX!' if is_max else f'다음까지 {xp_need - xp_in} XP'}</span>
                    </div>
                </div>
                """
                target = col_a if i % 2 == 0 else col_b
                target.markdown(card_html, unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

# ══════════════════════════════════════════════
#  탭 3: 멘토 랭킹
# ══════════════════════════════════════════════
with tab3:
    st.markdown("#### 👑 멘토 포인트 랭킹")
    st.markdown(
        '<p style="color:#6B7280;font-size:0.82rem;margin-bottom:1rem">'
        '친구를 도와줄수록 멘토 포인트가 쌓여요! (본인 지목·미지목 제외)</p>',
        unsafe_allow_html=True
    )

    if mentor_col and "본인 이름" in df_f.columns:
        mentor_df = df_f[
            (df_f[mentor_col] != NO_MENTOR) &
            (df_f[mentor_col] != "") &
            (df_f[mentor_col].notna()) &
            (df_f[mentor_col] != df_f["본인 이름"])
        ]
        mentor_counts = (
            mentor_df.groupby(mentor_col).size()
            .reset_index(name="포인트")
            .sort_values("포인트", ascending=False)
        )

        if mentor_counts.empty:
            st.info("아직 멘토 지목 데이터가 없습니다.")
        else:
            col_chart, col_list = st.columns([3, 2])

            with col_list:
                top15 = mentor_counts.head(15)
                for i, (_, row) in enumerate(top15.iterrows()):
                    rank_icons = ["🥇","🥈","🥉"] + ["🌟"] * 12
                    r_icon = rank_icons[i]
                    bar_pct = int(row["포인트"] / top15["포인트"].max() * 100)
                    st.markdown(f"""
                    <div class="mentor-card">
                        <div class="m-rank">{r_icon}</div>
                        <div class="m-info">
                            <div class="m-name">{row[mentor_col]}</div>
                            <div style="background:#0F0F1A;border-radius:4px;height:6px;margin:0.3rem 0">
                                <div style="width:{bar_pct}%;height:6px;border-radius:4px;background:linear-gradient(90deg,#7C3AED,#A78BFA)"></div>
                            </div>
                        </div>
                        <div class="m-score">+{row["포인트"]}pt</div>
                    </div>
                    """, unsafe_allow_html=True)

            with col_chart:
                top10 = mentor_counts.head(10)
                fig2 = go.Figure(go.Bar(
                    x=top10["포인트"],
                    y=top10[mentor_col],
                    orientation="h",
                    marker=dict(
                        color=top10["포인트"],
                        colorscale=[[0,"#4C1D95"],[1,"#A78BFA"]],
                        showscale=False,
                    ),
                    text=top10["포인트"].astype(str) + "pt",
                    textposition="outside",
                    textfont=dict(color="#A78BFA", size=12),
                ))
                fig2.update_layout(
                    paper_bgcolor="#0F0F1A", plot_bgcolor="#0F0F1A",
                    font_color="#9CA3AF",
                    xaxis=dict(gridcolor="#1E1E3A", tickfont_color="#6B7280"),
                    yaxis=dict(
                        categoryorder="total ascending",
                        tickfont=dict(color="#E0E7FF", size=12),
                    ),
                    height=420, margin=dict(t=10, b=10, l=10, r=60),
                    title=dict(text="TOP 10 멘토", font=dict(color="#A78BFA", size=14), x=0.5),
                )
                st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("멘토 이름 컬럼을 찾을 수 없습니다.")

# ══════════════════════════════════════════════
#  탭 4: 반별 현황
# ══════════════════════════════════════════════
with tab4:
    st.markdown("#### 🏰 반별 퀘스트 현황")

    col_5, col_6 = st.columns(2)

    for col_widget, class_name in zip([col_5, col_6], ALL_STUDENTS.keys()):
        if class_name not in class_filter:
            continue

        students = ALL_STUDENTS[class_name]
        class_df = df_f[df_f["반"] == class_name] if "반" in df_f.columns else df_f
        total = len(students)

        # 제출자 계산
        submitted_set = set()
        if "본인 이름" in class_df.columns:
            submitted_set = set(class_df["본인 이름"].unique())
        submitted_cnt = len([s for s in students if s in submitted_set])
        rate = submitted_cnt / total * 100 if total > 0 else 0

        # 반 평균 레벨
        levels = []
        for name in students:
            s_cnt = class_df[class_df["본인 이름"] == name]["차시"].nunique() if "본인 이름" in class_df.columns else 0
            lv, *_ = get_level_info(s_cnt)
            levels.append(lv)
        avg_lv = sum(levels) / len(levels) if levels else 0

        with col_widget:
            st.markdown(f"""
            <div class="class-card">
                <h3>🏰 {class_name}</h3>
                <div style="display:flex;gap:1rem;margin-bottom:1rem">
                    <div style="flex:1;text-align:center">
                        <div style="font-size:1.8rem;font-weight:900;color:#E0E7FF">{submitted_cnt}/{total}</div>
                        <div style="font-size:0.72rem;color:#6B7280">참여 학생</div>
                    </div>
                    <div style="flex:1;text-align:center">
                        <div style="font-size:1.8rem;font-weight:900;color:#A78BFA">{avg_lv:.1f}</div>
                        <div style="font-size:0.72rem;color:#6B7280">평균 레벨</div>
                    </div>
                    <div style="flex:1;text-align:center">
                        <div style="font-size:1.8rem;font-weight:900;color:#34D399">{rate:.0f}%</div>
                        <div style="font-size:0.72rem;color:#6B7280">참여율</div>
                    </div>
                </div>
                <div style="background:#0F0F1A;border-radius:8px;height:12px;overflow:hidden;margin-bottom:0.5rem">
                    <div style="width:{rate}%;height:12px;border-radius:8px;
                        background:linear-gradient(90deg,#7C3AED,#34D399);
                        transition:width 0.5s ease"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # 미제출 학생
            not_submitted = [s for s in students if s not in submitted_set]
            if not_submitted:
                with st.expander(f"⚠️ 미참여 학생 {len(not_submitted)}명"):
                    st.markdown(
                        '<div style="color:#9CA3AF;font-size:0.85rem">' +
                        "  ·  ".join(not_submitted) +
                        '</div>',
                        unsafe_allow_html=True
                    )
            else:
                st.markdown(
                    '<div style="color:#34D399;font-size:0.85rem;'
                    'text-align:center;padding:0.5rem">✅ 전원 퀘스트 참여 완료!</div>',
                    unsafe_allow_html=True
                )

        # 레벨 분포 파이
        lv_dist = {f"Lv.{lv}": 0 for _, _, lv, _, _, _ in LEVEL_TABLE}
        for name in students:
            s_cnt = class_df[class_df["본인 이름"] == name]["차시"].nunique() if "본인 이름" in class_df.columns else 0
            lv, *_ = get_level_info(s_cnt)
            lv_dist[f"Lv.{lv}"] = lv_dist.get(f"Lv.{lv}", 0) + 1

        fig3 = go.Figure(go.Pie(
            labels=list(lv_dist.keys()),
            values=list(lv_dist.values()),
            hole=0.55,
            marker=dict(colors=["#EF9A9A","#FFB74D","#FFF176","#81C784","#64B5F6"]),
            textfont=dict(color="#0F0F1A", size=11),
        ))
        fig3.update_layout(
            paper_bgcolor="#0F0F1A",
            font_color="#9CA3AF",
            showlegend=True,
            legend=dict(font=dict(color="#9CA3AF", size=10)),
            height=240,
            margin=dict(t=10, b=10, l=10, r=10),
            annotations=[dict(
                text=f"Lv.{avg_lv:.1f}", x=0.5, y=0.5, showarrow=False,
                font=dict(size=18, color="#E0E7FF", family="Noto Sans KR")
            )],
        )
        with col_widget:
            st.plotly_chart(fig3, use_container_width=True)
