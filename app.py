import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import plotly.express as px
from datetime import datetime

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
TOTAL_LESSONS = 19

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
    except Exception as e:
        return pd.DataFrame()

    all_dfs = []
    for worksheet in sh.worksheets():
        try:
            raw = worksheet.get_all_values()
            if len(raw) < 2:
                continue

            headers = raw[0]
            rows = raw[1:]

            # 중복 컬럼 처리
            seen = {}
            clean_headers = []
            for h in headers:
                if h in seen:
                    seen[h] += 1
                    clean_headers.append(f"{h}_{seen[h]}")
                else:
                    seen[h] = 1
                    clean_headers.append(h)

            df = pd.DataFrame(rows, columns=clean_headers)
            df = df[df.iloc[:, 0] != ""].copy()
            if df.empty:
                continue

            # 차시 이름 정리 (3. "Form Responses 문제 해결)
            lesson_title = worksheet.title
            # "01_1차시 - 수열의 뜻" 형식이면 앞 번호 제거
            if "_" in lesson_title:
                lesson_title = lesson_title.split("_", 1)[1]
            # "Form Responses N" 형식이면 탭 순서로 차시 표기
            if lesson_title.startswith("Form Responses"):
                lesson_title = worksheet.title
            df["차시"] = lesson_title

            # 중복 컬럼 통합
            for base_col in ["본인 이름", "도움 준 멘토 이름"]:
                dup_col = base_col + "_2"
                if base_col in df.columns and dup_col in df.columns:
                    df[base_col] = df[base_col].replace("", pd.NA).fillna(df[dup_col])
                    df.drop(columns=[dup_col], inplace=True)
                elif dup_col in df.columns and base_col not in df.columns:
                    df.rename(columns={dup_col: base_col}, inplace=True)

            # 타임스탬프
            ts_col = clean_headers[0]
            if ts_col:
                df.rename(columns={ts_col: "타임스탬프"}, inplace=True)
                df["타임스탬프"] = pd.to_datetime(df["타임스탬프"], errors="coerce")

            all_dfs.append(df)
        except Exception:
            continue

    if not all_dfs:
        return pd.DataFrame()
    return pd.concat(all_dfs, ignore_index=True)

# ────────────────────────────────────────────────
#  헤더
# ────────────────────────────────────────────────
st.title("📊 수열 학습 대시보드")
st.caption("대동세무고등학교 · 대수 | 데이터는 5분마다 자동 갱신됩니다")

col_title, col_btn = st.columns([6, 1])
with col_btn:
    if st.button("🔄 새로고침"):
        st.cache_data.clear()
        st.rerun()

df = load_all_responses()

if df.empty:
    st.warning("아직 응답 데이터가 없습니다.")
    st.stop()

# ────────────────────────────────────────────────
#  사이드바 필터
# ────────────────────────────────────────────────
with st.sidebar:
    st.header("🔍 필터")
    class_filter = st.multiselect(
        "반 선택",
        options=list(ALL_STUDENTS.keys()),
        default=list(ALL_STUDENTS.keys())
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
    df_filtered = df.copy()

# ────────────────────────────────────────────────
#  탭
# ────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📋 차시별 제출 현황",
    "👤 개인별 제출 현황",   # ← 새로 추가
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
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(
            xaxis_tickangle=-45,
            showlegend=False,
            height=420,
            coloraxis_showscale=False,
            xaxis_title="차시",
            yaxis_title="제출 수"
        )
        st.plotly_chart(fig, use_container_width=True)

        total_students = sum(len(v) for k, v in ALL_STUDENTS.items() if k in class_filter)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("전체 응답 수", len(df_filtered))
        c2.metric("차시당 평균", f"{lesson_counts['제출 수'].mean():.1f}")
        c3.metric("최다 제출 차시",
                  lesson_counts.loc[lesson_counts['제출 수'].idxmax(), '차시'][-8:])
        c4.metric("필터 학생 수", f"{total_students}명")

# ────────── 탭 2: 개인별 제출 현황 (신규) ──────────
with tab2:
    st.subheader("👤 개인별 제출 현황")
    st.caption("학생별로 몇 차시를 제출했는지 확인합니다. 빈칸이 있으면 미제출 차시예요.")

    if "본인 이름" not in df_filtered.columns or "차시" not in df_filtered.columns:
        st.info("본인 이름 또는 차시 데이터를 찾을 수 없습니다.")
    else:
        # 전체 차시 목록
        all_lessons = sorted(df_filtered["차시"].unique().tolist())

        # 반 탭으로 나누기
        class_tabs = st.tabs(list(ALL_STUDENTS.keys()))
        for cls_idx, (class_name, students) in enumerate(ALL_STUDENTS.items()):
            if class_name not in class_filter:
                continue
            with class_tabs[cls_idx]:
                class_df = df_filtered[df_filtered["반"] == class_name] \
                    if "반" in df_filtered.columns else df_filtered

                # 학생 × 차시 피벗 테이블
                rows = []
                for student in students:
                    student_df = class_df[class_df["본인 이름"] == student]
                    submitted_lessons = set(student_df["차시"].unique())
                    total_submitted = len(submitted_lessons)
                    row = {"이름": student, "제출 수": f"{total_submitted}/{len(all_lessons)}"}
                    for lesson in all_lessons:
                        row[lesson[-6:]] = "✅" if lesson in submitted_lessons else "❌"
                    rows.append(row)

                pivot_df = pd.DataFrame(rows)

                # 제출 수 기준 정렬
                pivot_df["_sort"] = pivot_df["제출 수"].apply(
                    lambda x: int(x.split("/")[0])
                )
                pivot_df = pivot_df.sort_values("_sort", ascending=False).drop(columns=["_sort"])

                st.dataframe(pivot_df, hide_index=True, use_container_width=True)

                # 미제출 학생 요약
                not_complete = pivot_df[
                    pivot_df["제출 수"].apply(lambda x: int(x.split("/")[0])) < len(all_lessons)
                ]
                if not not_complete.empty:
                    st.warning(f"⚠️ 미완료 학생 {len(not_complete)}명")
                    missing_summary = []
                    for _, row in not_complete.iterrows():
                        missing_lessons = [
                            l[-6:] for l in all_lessons
                            if row.get(l[-6:], "❌") == "❌"
                        ]
                        missing_summary.append(
                            f"**{row['이름']}**: {', '.join(missing_lessons)} 미제출"
                        )
                    with st.expander("미제출 상세 보기"):
                        for s in missing_summary:
                            st.markdown(s)
                else:
                    st.success(f"✅ {class_name} 전원 모든 차시 제출 완료!")

                # 개인별 제출 수 막대그래프
                bar_df = pivot_df[["이름", "제출 수"]].copy()
                bar_df["제출 수(숫자)"] = bar_df["제출 수"].apply(
                    lambda x: int(x.split("/")[0])
                )
                fig_personal = px.bar(
                    bar_df.sort_values("제출 수(숫자)"),
                    x="제출 수(숫자)",
                    y="이름",
                    orientation="h",
                    color="제출 수(숫자)",
                    color_continuous_scale="Blues",
                    text="제출 수",
                    range_color=[0, len(all_lessons)],
                    title=f"{class_name} 개인별 제출 현황"
                )
                fig_personal.update_traces(textposition="outside")
                fig_personal.update_layout(
                    coloraxis_showscale=False,
                    height=500,
                    xaxis_title="제출 차시 수",
                    yaxis_title=""
                )
                st.plotly_chart(fig_personal, use_container_width=True)

# ────────── 탭 3: 멘토 점수 순위 ──────────
with tab3:
    st.subheader("🏆 멘토 점수 순위")
    st.caption("도움 준 멘토로 지목된 횟수 (본인 지목 제외)")

    mentor_col = next(
        (c for c in ["도움 준 멘토 이름", "멘토 이름"] if c in df_filtered.columns),
        None
    )
    student_col = "본인 이름" if "본인 이름" in df_filtered.columns else None

    if mentor_col:
        mentor_df = df_filtered[
            (df_filtered[mentor_col] != NO_MENTOR) &
            (df_filtered[mentor_col] != "") &
            (df_filtered[mentor_col].notna())
        ]
        if student_col:
            mentor_df = mentor_df[mentor_df[mentor_col] != mentor_df[student_col]]

        mentor_counts = (
            mentor_df.groupby(mentor_col)
            .size()
            .reset_index(name="멘토 점수")
            .sort_values("멘토 점수", ascending=False)
            .head(15)
        )

        if not mentor_counts.empty:
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

# ────────── 탭 4: 반별 참여율 ──────────
with tab4:
    st.subheader("👥 반별 참여 현황")

    student_col = "본인 이름" if "본인 이름" in df_filtered.columns else None
    if "반" in df_filtered.columns and student_col:
        col_a, col_b = st.columns(2)
        for idx, (class_name, students) in enumerate(ALL_STUDENTS.items()):
            if class_name not in class_filter:
                continue
            class_df = df_filtered[df_filtered["반"] == class_name]
            submitted = class_df[student_col].nunique()
            total = len(students)
            rate = submitted / total * 100 if total > 0 else 0
            submitted_names = set(class_df[student_col].unique())
            not_submitted = [s for s in students if s not in submitted_names]

            target_col = col_a if idx == 0 else col_b
            with target_col:
                st.markdown(f"### {class_name}")
                st.metric("참여율", f"{rate:.0f}%", f"{submitted}/{total}명 제출")
                st.progress(rate / 100)
                if not_submitted:
                    with st.expander(f"미제출 학생 {len(not_submitted)}명 보기"):
                        st.write(", ".join(not_submitted))
                else:
                    st.success("✅ 전원 제출 완료!")
    else:
        st.info("반 또는 학생 이름 데이터를 찾을 수 없습니다.")

# ────────── 탭 5: 시간대별 응답 ──────────
with tab5:
    st.subheader("📅 시간대별 응답 분포")

    if "타임스탬프" in df_filtered.columns:
        time_df = df_filtered.dropna(subset=["타임스탬프"]).copy()
        time_df["시간대"] = time_df["타임스탬프"].dt.hour
        time_df["날짜"] = time_df["타임스탬프"].dt.date

        col_t1, col_t2 = st.columns(2)
        with col_t1:
            hour_counts = time_df.groupby("시간대").size().reset_index(name="응답 수")
            fig3 = px.bar(
                hour_counts, x="시간대", y="응답 수",
                title="시간대별 응답 수 (0~23시)",
                color="응답 수", color_continuous_scale="Oranges"
            )
            fig3.update_layout(coloraxis_showscale=False)
            st.plotly_chart(fig3, use_container_width=True)

        with col_t2:
            date_counts = time_df.groupby("날짜").size().reset_index(name="응답 수")
            fig4 = px.line(
                date_counts, x="날짜", y="응답 수",
                title="날짜별 응답 추이", markers=True
            )
            st.plotly_chart(fig4, use_container_width=True)
    else:
        st.info("타임스탬프 데이터를 찾을 수 없습니다.")
