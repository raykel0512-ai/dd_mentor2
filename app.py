import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
st.write("👋 앱 로드됨")
st.write(st.secrets)
# ────────────────────────────────────────────────
#  설정
# ────────────────────────────────────────────────
st.set_page_config(
    page_title="수열 학습 대시보드",
    page_icon="📊",
    layout="wide"
)

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

@st.cache_data(ttl=300)  # 5분마다 갱신
def load_all_responses():
    """모든 차시 응답을 하나의 DataFrame으로 통합"""
    gc = get_gc()
    try:
        sh = gc.open("수열_폼_응답_통합")
    except Exception as e:
        st.error(f"❌ '수열_폼_응답_통합' 시트를 열 수 없습니다: {e}")
        return pd.DataFrame()

    all_dfs = []
    for worksheet in sh.worksheets():
        try:
            data = worksheet.get_all_records()
            if not data:
                continue
            df = pd.DataFrame(data)

            # 차시 이름 추출 (탭 이름 기준: "01_1차시 - ...")
            lesson_title = worksheet.title
            if "_" in lesson_title:
                lesson_title = lesson_title.split("_", 1)[1]
            df["차시"] = lesson_title

            # 컬럼명 표준화 (폼마다 약간 다를 수 있음)
            df.columns = [c.strip() for c in df.columns]
            all_dfs.append(df)
        except Exception as e:
            continue

    if not all_dfs:
        return pd.DataFrame()

    combined = pd.concat(all_dfs, ignore_index=True)

    # 타임스탬프 파싱
    if "타임스탬프" in combined.columns:
        combined["타임스탬프"] = pd.to_datetime(
            combined["타임스탬프"], errors="coerce"
        )
    return combined

# ────────────────────────────────────────────────
#  UI
# ────────────────────────────────────────────────
st.title("📊 수열 학습 대시보드")
st.caption("대동세무고등학교 · 대수 | 데이터는 5분마다 자동 갱신됩니다")

# 수동 갱신 버튼
col_title, col_btn = st.columns([6, 1])
with col_btn:
    if st.button("🔄 새로고침"):
        st.cache_data.clear()
        st.rerun()

# 데이터 로드
df = load_all_responses()

if df.empty:
    st.warning("아직 응답 데이터가 없거나 시트 연결을 확인해주세요.")
    with st.expander("🔧 연결 진단"):
        st.write("**1. Secrets 확인**")
        if "gcp_service_account" in st.secrets:
            st.success("✅ gcp_service_account 키 존재")
            st.write("client_email:", st.secrets["gcp_service_account"].get("client_email", "없음"))
        else:
            st.error("❌ gcp_service_account 키 없음")

        st.write("**2. 시트 연결 및 컬럼 확인**")
        try:
            gc2 = get_gc()
            st.success("✅ Google 인증 성공")
            try:
                sh2 = gc2.open("수열_폼_응답_통합")
                st.success("✅ 시트 연결 성공")
                tabs2 = [w.title for w in sh2.worksheets()]
                st.write("탭 목록:", tabs2)

                # 데이터 있는 첫 탭 찾아서 컬럼 확인
                st.write("**3. 컬럼명 확인**")
                for ws in sh2.worksheets():
                    try:
                        data = ws.get_all_records()
                        if data:
                            st.write(f"탭 `{ws.title}` 컬럼명:")
                            st.write(list(data[0].keys()))
                            st.write("첫 번째 행 샘플:")
                            st.write(data[0])
                            break
                    except Exception as e:
                        st.write(f"탭 `{ws.title}` 읽기 실패: {e}")
                        continue
            except Exception as e:
                st.error(f"❌ 시트 열기 실패: {e}")
        except Exception as e:
            st.error(f"❌ Google 인증 실패: {e}")
    st.stop()

# ────────────────────────────────────────────────
#  사이드바 필터
# ────────────────────────────────────────────────
with st.sidebar:
    st.header("🔍 필터")
    class_filter = st.multiselect(
        "반 선택",
        options=["2학년 5반", "2학년 6반"],
        default=["2학년 5반", "2학년 6반"]
    )
    st.divider()
    st.caption(f"전체 응답 수: {len(df)}건")
    if "타임스탬프" in df.columns:
        latest = df["타임스탬프"].max()
        if pd.notna(latest):
            st.caption(f"최근 응답: {latest.strftime('%m/%d %H:%M')}")

# 반 필터 적용
if "반" in df.columns and class_filter:
    df_filtered = df[df["반"].isin(class_filter)]
else:
    df_filtered = df

# ────────────────────────────────────────────────
#  탭 구성
# ────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "📋 차시별 제출 현황",
    "🏆 멘토 점수 순위",
    "👥 반별 참여율",
    "📅 시간대별 응답"
])

# ────────── 탭 1: 차시별 제출 현황 ──────────
with tab1:
    st.subheader("차시별 제출 횟수")

    if "차시" in df_filtered.columns:
        lesson_counts = (
            df_filtered.groupby("차시")
            .size()
            .reset_index(name="제출 수")
            .sort_values("차시")
        )

        fig = px.bar(
            lesson_counts,
            x="차시",
            y="제출 수",
            color="제출 수",
            color_continuous_scale="Blues",
            text="제출 수",
            title="차시별 제출 횟수"
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(
            xaxis_tickangle=-45,
            showlegend=False,
            height=400,
            coloraxis_showscale=False
        )
        st.plotly_chart(fig, use_container_width=True)

        # 요약 지표
        total_students = sum(len(v) for v in ALL_STUDENTS.values())
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("전체 응답 수", len(df_filtered))
        c2.metric("평균 제출 수 (차시당)", f"{lesson_counts['제출 수'].mean():.1f}")
        c3.metric("가장 많이 제출한 차시", lesson_counts.loc[lesson_counts['제출 수'].idxmax(), '차시'][-6:])
        c4.metric("전체 학생 수", total_students)
    else:
        st.info("차시 데이터를 불러올 수 없습니다.")

# ────────── 탭 2: 멘토 점수 순위 ──────────
with tab2:
    st.subheader("🏆 멘토 점수 순위")
    st.caption("도움 준 멘토로 지목된 횟수 (본인 지목 제외)")

    mentor_col = None
    for col in ["도움 준 멘토 이름", "멘토 이름"]:
        if col in df_filtered.columns:
            mentor_col = col
            break
    student_col = "본인 이름" if "본인 이름" in df_filtered.columns else None

    if mentor_col:
        mentor_df = df_filtered[
            (df_filtered[mentor_col] != NO_MENTOR) &
            (df_filtered[mentor_col] != "") &
            (df_filtered[mentor_col].notna())
        ]
        # 본인 = 멘토 제외
        if student_col:
            mentor_df = mentor_df[
                mentor_df[mentor_col] != mentor_df[student_col]
            ]

        mentor_counts = (
            mentor_df.groupby(mentor_col)
            .size()
            .reset_index(name="멘토 점수")
            .sort_values("멘토 점수", ascending=False)
            .head(15)
        )

        if not mentor_counts.empty:
            # 순위 컬럼 추가
            mentor_counts.insert(0, "순위", range(1, len(mentor_counts) + 1))
            medals = {1: "🥇", 2: "🥈", 3: "🥉"}
            mentor_counts["순위"] = mentor_counts["순위"].map(
                lambda x: medals.get(x, str(x))
            )

            col_chart, col_table = st.columns([3, 2])
            with col_chart:
                fig2 = px.bar(
                    mentor_counts.head(10),
                    x="멘토 점수",
                    y=mentor_col,
                    orientation="h",
                    color="멘토 점수",
                    color_continuous_scale="Greens",
                    text="멘토 점수",
                    title="멘토 점수 TOP 10"
                )
                fig2.update_traces(textposition="outside")
                fig2.update_layout(
                    yaxis={"categoryorder": "total ascending"},
                    showlegend=False,
                    height=400,
                    coloraxis_showscale=False
                )
                st.plotly_chart(fig2, use_container_width=True)

            with col_table:
                st.dataframe(
                    mentor_counts.rename(columns={mentor_col: "멘토 이름"}),
                    hide_index=True,
                    use_container_width=True
                )
        else:
            st.info("아직 멘토 지목 데이터가 없습니다.")
    else:
        st.info("멘토 이름 컬럼을 찾을 수 없습니다.")

# ────────── 탭 3: 반별 참여율 ──────────
with tab3:
    st.subheader("👥 반별 참여 현황")

    if "반" in df_filtered.columns and student_col:
        col_a, col_b = st.columns(2)

        for idx, (class_name, students) in enumerate(ALL_STUDENTS.items()):
            if class_name not in class_filter:
                continue

            class_df = df_filtered[df_filtered["반"] == class_name]
            submitted = class_df[student_col].nunique()
            total = len(students)
            rate = submitted / total * 100 if total > 0 else 0

            # 미제출 학생
            submitted_names = set(class_df[student_col].unique())
            not_submitted = [s for s in students if s not in submitted_names]

            target_col = col_a if idx == 0 else col_b
            with target_col:
                st.markdown(f"### {class_name}")
                st.metric(
                    "참여율",
                    f"{rate:.0f}%",
                    f"{submitted}/{total}명 제출"
                )

                # 진행바
                st.progress(rate / 100)

                # 미제출 학생 목록
                if not_submitted:
                    with st.expander(f"미제출 학생 {len(not_submitted)}명 보기"):
                        st.write(", ".join(not_submitted))
                else:
                    st.success("✅ 전원 제출 완료!")
    else:
        st.info("반 또는 학생 이름 데이터를 찾을 수 없습니다.")

# ────────── 탭 4: 시간대별 응답 ──────────
with tab4:
    st.subheader("📅 시간대별 응답 분포")

    if "타임스탬프" in df_filtered.columns:
        time_df = df_filtered.dropna(subset=["타임스탬프"]).copy()
        time_df["시간대"] = time_df["타임스탬프"].dt.hour
        time_df["날짜"] = time_df["타임스탬프"].dt.date

        col_t1, col_t2 = st.columns(2)

        with col_t1:
            hour_counts = time_df.groupby("시간대").size().reset_index(name="응답 수")
            fig3 = px.bar(
                hour_counts,
                x="시간대",
                y="응답 수",
                title="시간대별 응답 수 (0~23시)",
                color="응답 수",
                color_continuous_scale="Oranges"
            )
            fig3.update_layout(coloraxis_showscale=False)
            st.plotly_chart(fig3, use_container_width=True)

        with col_t2:
            date_counts = time_df.groupby("날짜").size().reset_index(name="응답 수")
            fig4 = px.line(
                date_counts,
                x="날짜",
                y="응답 수",
                title="날짜별 응답 추이",
                markers=True
            )
            st.plotly_chart(fig4, use_container_width=True)
    else:
        st.info("타임스탬프 데이터를 찾을 수 없습니다.")
# ── 임시 디버그 (확인 후 삭제) ──────────────────
with st.expander("🔧 연결 진단"):
    st.write("**1. Secrets 확인**")
    if "gcp_service_account" in st.secrets:
        st.success("✅ gcp_service_account 키 존재")
        st.write("client_email:", st.secrets["gcp_service_account"].get("client_email", "없음"))
    else:
        st.error("❌ gcp_service_account 키 없음")

    st.write("**2. 시트 연결 확인**")
    try:
        gc = get_gc()
        st.success("✅ Google 인증 성공")
        try:
            sh = gc.open("수열_폼_응답_통합")
            st.success("✅ 시트 연결 성공")
            tabs = [w.title for w in sh.worksheets()]
            st.write("탭 목록:", tabs)
        except Exception as e:
            st.error(f"❌ 시트 열기 실패: {e}")
    except Exception as e:
        st.error(f"❌ Google 인증 실패: {e}")
