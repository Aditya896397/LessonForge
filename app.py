"""LessonForge - Streamlit UI.

Run with:  streamlit run app.py
"""
from __future__ import annotations

import re
from dataclasses import replace

import streamlit as st

from lessonforge.config import get_settings
from lessonforge.export import build_zip, qc1_markdown, qc2_markdown, references_markdown, to_html
from lessonforge.llm import LLMError
from lessonforge.models import STEP_LABELS, STEP_ORDER, LessonProject, QCIssue
from lessonforge.pipeline import Pipeline, validate_inputs
from lessonforge.revise import revise_lesson, unified_diff
from lessonforge.storage import ProjectStore, add_version
from lessonforge.timing import analyse_timing

st.set_page_config(page_title="LessonForge: AI Lesson Creator", page_icon="📘", layout="wide")

SAMPLES = {
    "HTTP Requests and Responses (sample from brief)": (
        "HTTP Requests and Responses",
        "Explain GET and POST methods and distinguish between 2xx, 4xx, and 5xx response status categories.",
    ),
    "Git Branching and Merging (second test topic)": (
        "Git Branching and Merging",
        "Create and switch between Git branches, merge a feature branch into main, and resolve a simple "
        "merge conflict.",
    ),
}
STATUS_ICON = {"pending": "⚪", "running": "🔄", "done": "✅", "failed": "❌", "stale": "🟡"}
SEV_ICON = {"critical": "🔴", "major": "🟠", "minor": "🔵"}


# --------------------------------------------------------------------------- #
# Setup
# --------------------------------------------------------------------------- #
def settings():
    base = get_settings()
    ss = st.session_state
    return replace(base,
                   gemini_api_key=ss.get("api_key_override") or base.gemini_api_key,
                   model=ss.get("model_override") or base.model,
                   qc_model=ss.get("qc_model_override") or base.qc_model)


@st.cache_resource
def store_for(path: str) -> ProjectStore:
    return ProjectStore(path)


def store() -> ProjectStore:
    return store_for(str(get_settings().data_dir))


def pipeline() -> Pipeline:
    return Pipeline(store(), settings())


def load_project() -> LessonProject | None:
    pid = st.session_state.get("pid")
    if not pid:
        return None
    try:
        return store().load(pid)
    except (FileNotFoundError, ValueError):
        st.session_state.pop("pid", None)
        return None


def show_table(rows: list[dict], links: tuple[str, ...] = ("url",)) -> None:
    """Render rows as a Markdown table. (Avoids st.dataframe, which needs pyarrow:
    some Windows machines block pyarrow's DLLs via Application Control.)"""
    if not rows:
        st.caption("(none)")
        return
    cols = list(rows[0].keys())

    def cell(k, v):
        if v is None or v == "":
            return ""
        text = re.sub(r"\s+", " ", str(v)).replace("|", "\\|")
        if k in links:
            urls = [u for u in text.split() if u.startswith("http")]
            return " ".join(f"[link{'' if len(urls) == 1 else n + 1}]({u})" for n, u in enumerate(urls))
        return text
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    lines += ["| " + " | ".join(cell(k, r.get(k)) for k in cols) + " |" for r in rows]
    st.markdown("\n".join(lines))


def strip_comments(md: str) -> str:
    return re.sub(r"<!--.*?-->\n?", "", md, flags=re.DOTALL)


# --------------------------------------------------------------------------- #
# Sidebar
# --------------------------------------------------------------------------- #
def sidebar() -> None:
    s = settings()
    with st.sidebar:
        st.title("📘 LessonForge")
        st.caption("Research-grounded 45-minute lessons with two QC layers.")
        if st.button("➕ New lesson", width="stretch"):
            st.session_state.pop("pid", None)
            st.session_state.pop("proposal", None)
            st.rerun()

        st.subheader("Saved lessons")
        projects = store().list()
        if not projects:
            st.caption("None yet.")
        for p in projects[:30]:
            label = f"{p.title} · v{p.current_version}" if p.versions else f"{p.title} · (no lesson)"
            if st.button(label, key=f"open-{p.id}", width="stretch",
                         type="primary" if p.id == st.session_state.get("pid") else "secondary"):
                st.session_state["pid"] = p.id
                st.session_state.pop("proposal", None)
                st.rerun()

        with st.expander("⚙️ Settings", expanded=not s.gemini_api_key):
            if s.gemini_api_key:
                st.success("Gemini API key loaded.")
            else:
                st.warning("No GEMINI_API_KEY found in .env.")
            st.text_input("Gemini API key (this session only)", type="password", key="api_key_override",
                          help="Overrides .env for this browser session. Free key: aistudio.google.com/apikey")
            st.text_input("Generation model", value=s.model, key="model_override")
            st.text_input("Fact-check (QC1) model", value=s.qc_model, key="qc_model_override")
            st.caption(f"YouTube: {'Data API key' if s.youtube_api_key else 'public search (no key)'}")


# --------------------------------------------------------------------------- #
# New lesson
# --------------------------------------------------------------------------- #
def new_lesson_page() -> None:
    st.header("Create a lesson")
    st.write("Enter a lesson title and learning objective. The tool researches websites, books and "
             "YouTube, writes a 45-minute lesson, then runs two independent quality checks.")
    cols = st.columns(len(SAMPLES))
    for col, (label, (t, o)) in zip(cols, SAMPLES.items()):
        if col.button(f"Use: {label}", width="stretch"):
            st.session_state["in_title"], st.session_state["in_obj"] = t, o
            st.rerun()
    with st.form("new"):
        title = st.text_input("Lesson title", key="in_title", max_chars=200)
        objective = st.text_area("Learning objective", key="in_obj", height=100, max_chars=800)
        go = st.form_submit_button("🚀 Research & generate", type="primary")
    if go:
        errors = validate_inputs(title, objective)
        if errors:
            for e in errors:
                st.error(e)
            return
        project = store().create(title, objective)
        st.session_state["pid"] = project.id
        run_pipeline(project)
        st.rerun()


def run_pipeline(project: LessonProject) -> None:
    pl = pipeline()
    with st.status("Working on your lesson…", expanded=True) as status:
        msgs = {"research": "🔎 Researching websites, books and YouTube videos…",
                "generate": "✍️ Writing the lesson…",
                "qc": "🧪 Running QC 1 (fact check) and QC 2 (instructional review) in parallel…"}

        def progress(step: str, state: str) -> None:
            if state == "running":
                status.write(msgs[step])
            elif state == "done":
                status.write(f"✅ {step.upper() if step == 'qc' else step.capitalize()} finished")
            else:
                status.write(f"❌ {step} failed (see the pipeline panel to retry)")

        ok = pl.run_all(project, progress)
        status.update(label="Done" if ok else "Stopped: a step failed", state="complete" if ok else "error")


# --------------------------------------------------------------------------- #
# Project page
# --------------------------------------------------------------------------- #
def pipeline_panel(p: LessonProject) -> None:
    cols = st.columns(len(STEP_ORDER) + 1)
    for col, step in zip(cols, STEP_ORDER):
        stt = p.steps[step]
        col.markdown(f"**{STATUS_ICON[stt.status]} {STEP_LABELS[step]}**  \n"
                     f"<small>{stt.status}{f' · attempts: {stt.attempts}' if stt.attempts else ''}</small>",
                     unsafe_allow_html=True)
        if stt.status == "failed":
            col.error(stt.error, icon="⚠️")
        label = {"failed": "Retry", "stale": "Re-run", "pending": "Run", "done": "Re-run"}.get(stt.status, "Run")
        if col.button(f"↻ {label}", key=f"run-{step}", disabled=stt.status == "running"):
            if step == "generate" and p.versions and not st.session_state.get(f"confirm-gen-{p.id}"):
                st.session_state[f"confirm-gen-{p.id}"] = True
                st.rerun()
            with st.spinner(f"Running {STEP_LABELS[step]}…"):
                pipeline().run_step(p, step)
            st.session_state.pop(f"confirm-gen-{p.id}", None)
            st.rerun()
    with cols[-1]:
        pending = [s for s in STEP_ORDER if p.steps[s].status != "done"]
        if pending and st.button("▶ Run remaining steps", type="primary"):
            run_pipeline(p)
            st.rerun()
    if st.session_state.get(f"confirm-gen-{p.id}"):
        st.info("Regenerating creates a **new version**; your current lesson and edits stay in the "
                "Versions tab. Press the generation button again to confirm.")


def research_tab(p: LessonProject) -> None:
    r = p.research
    if not r:
        st.info("No research yet. Run the research step above.")
        return
    st.caption("Research method: " + ("Gemini + Google Search grounding" if r.method == "gemini-grounding"
               else "direct web retrieval (fetched pages, cited excerpts)"))
    for w in r.warnings:
        st.warning(w)
    c1, c2, c3 = st.columns(3)
    c1.metric("Web sources", len(r.sources))
    c2.metric("Verified books", len(r.books))
    c3.metric("Verified videos", len(r.videos))
    st.subheader("Web sources")
    show_table([{"id": s.id, "title": s.title, "url": s.url, "type": s.source_type, "trust prior": s.trust_hint,
                   "reachable": s.reachable, "http": s.http_status} for s in r.sources])
    st.subheader("Books (suggested by the model, verified in Google Books / Open Library)")
    show_table([{"id": b.id, "title": b.title, "author / publisher": b.publisher, "url": b.url,
                   "how found": b.source_type} for b in r.books])
    st.subheader("YouTube candidates (verified with YouTube oEmbed)")
    show_table([{"id": v.id, "title": v.title, "channel": v.channel, "duration": v.duration_text,
                   "views": v.views_text, "url": v.url} for v in r.videos])
    with st.expander("Research brief (with [S#] citations)"):
        st.markdown(r.notes)
    if r.search_queries:
        st.caption("Searches run: " + " · ".join(r.search_queries))


def editor_tab(p: LessonProject) -> None:
    if not p.versions:
        st.info("No lesson yet. Run lesson generation above.")
        return
    st.caption(f"Editing **v{p.current_version}** ({p.versions[-1].origin}). Saving creates a new version, "
               "so nothing is ever lost. Keep the `## N. Title (X min)` headings so the time check keeps working.")
    key = f"editor-{p.id}-{p.current_version}"
    text = st.text_area("Lesson Markdown", value=p.current_markdown, height=600, key=key,
                        label_visibility="collapsed")
    t = analyse_timing(text)
    st.caption(f"⏱ {t.note}")
    c1, c2, _ = st.columns([1, 1, 4])
    note = c2.text_input("Change note", key=f"note-{key}", placeholder="optional", label_visibility="collapsed")
    if c1.button("💾 Save as new version", type="primary", disabled=text == p.current_markdown):
        if not text.strip():
            st.error("The lesson cannot be empty.")
        else:
            add_version(p, text, "instructor edit", note)
            store().save(p)
            st.success(f"Saved v{p.current_version}. QC reports are now marked stale; re-run them when ready.")
            st.rerun()
    if text != p.current_markdown:
        st.warning("You have unsaved changes.")


def preview_tab(p: LessonProject) -> None:
    if not p.versions:
        st.info("No lesson yet.")
        return
    st.caption(f"Preview of v{p.current_version}")
    with st.container(border=True):
        st.markdown(strip_comments(p.current_markdown))
    if p.research and p.draft:
        vids = p.research.video_by_id()
        picks = [vids[x.video_ref] for x in p.draft.recommended_videos if x.video_ref in vids]
        if picks:
            st.subheader("Supplementary videos")
            cols = st.columns(min(3, len(picks)))
            for col, v in zip(cols, picks):
                col.video(v.url)
                col.caption(f"{v.title} · {v.channel}")


def stale_note(p: LessonProject, version: int) -> None:
    if version != p.current_version:
        st.warning(f"This report was produced for v{version}; the current lesson is v{p.current_version}. "
                   "Re-run this QC layer to audit the latest version.")


def issues_view(issues: list[QCIssue], p: LessonProject) -> None:
    if not issues:
        st.success("No issues found.")
        return
    for i in sorted(issues, key=lambda x: ["critical", "major", "minor"].index(x.severity)):
        tag = " ✅ applied" if i.id in p.applied_issue_ids else (" 🚫 dismissed" if i.id in p.dismissed_issue_ids else "")
        with st.expander(f"{SEV_ICON[i.severity]} {i.id} · {i.severity} · {i.category} · {i.location}{tag}"):
            if i.quote:
                st.markdown(f"> {i.quote}")
            st.markdown(f"**Problem:** {i.problem}\n\n**Suggestion:** {i.suggestion}")


def qc1_tab(p: LessonProject) -> None:
    r = p.qc1
    if not r:
        st.info("QC 1 has not run yet.")
        return
    stale_note(p, r.lesson_version)
    counts: dict[str, int] = {}
    for c in r.claims:
        counts[c.verdict] = counts.get(c.verdict, 0) + 1
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Accuracy score", f"{r.accuracy_score}/100")
    c2.metric("Claims checked", len(r.claims))
    c3.metric("Supported", counts.get("supported", 0))
    c4.metric("Problems", sum(v for k, v in counts.items() if k != "supported"))
    st.markdown(f"**Summary:** {r.summary}")
    st.subheader("Claim-by-claim verification (independent evidence: "
                 + ("Google Search" if r.verification_method == "gemini-grounding" else "freshly retrieved pages") + ")")
    show_table([{"verdict": c.verdict, "claim": c.claim, "section": c.location, "explanation": c.explanation,
                   "correction": c.correction, "evidence": c.evidence, "evidence links": " ".join(c.evidence_urls)}
                  for c in r.claims], links=("evidence links",))
    st.subheader("Source reliability & relevance")
    show_table([s.model_dump() for s in r.sources])
    st.subheader("Issues & suggested improvements")
    issues_view(r.issues, p)
    with st.expander("Verification searches and pages consulted"):
        st.markdown("**Searches:** " + (" · ".join(r.verification_queries) or "(none)"))
        for e in r.verification_sources:
            st.markdown(f"- [{e['title'] or e['url']}]({e['url']})")


def qc2_tab(p: LessonProject) -> None:
    r = p.qc2
    if not r:
        st.info("QC 2 has not run yet.")
        return
    stale_note(p, r.lesson_version)
    c1, c2, c3 = st.columns(3)
    c1.metric("Instructional score", f"{r.overall_score}/100")
    if r.timing:
        c2.metric("Declared minutes", f"{r.timing.declared_minutes} / {r.timing.budget_minutes}")
        c3.metric("Estimated minutes", f"{r.timing.estimated_total_minutes:.0f}")
    st.markdown(f"**Summary:** {r.summary}")
    st.subheader("Learning objective alignment")
    show_table([o.model_dump() for o in r.objective_coverage])
    st.subheader("Rubric")
    show_table([x.model_dump() for x in r.rubric])
    if r.timing:
        st.subheader("45-minute time check")
        st.caption(r.timing.note)
        show_table(r.timing.per_section)
    st.subheader("Automatic structure checks")
    for c in r.structure_checks:
        st.markdown(f"{'✅' if c['passed'] else '❌'} {c['check']} {('· ' + c['detail']) if c['detail'] else ''}")
    st.subheader("Issues & suggested improvements")
    issues_view(r.issues, p)


def apply_tab(p: LessonProject) -> None:
    if not p.versions:
        st.info("No lesson yet.")
        return
    proposal = st.session_state.get("proposal")
    if proposal and proposal["pid"] == p.id:
        st.subheader("Proposed revision")
        st.markdown("**Change log**\n" + "\n".join(f"- {c}" for c in proposal["change_log"]))
        t1, t2 = st.tabs(["Diff", "Preview"])
        with t1:
            st.code(unified_diff(p.current_markdown, proposal["markdown"]) or "(no changes)", language="diff")
        with t2:
            st.markdown(strip_comments(proposal["markdown"]))
        c1, c2 = st.columns(2)
        if c1.button("✅ Accept and save as new version", type="primary"):
            add_version(p, proposal["markdown"], "applied QC fixes" if proposal["ids"] else "AI edit",
                        "; ".join(proposal["ids"] + proposal["change_log"])[:1000])
            p.applied_issue_ids = sorted(set(p.applied_issue_ids) | set(proposal["ids"]))
            store().save(p)
            st.session_state.pop("proposal")
            st.success("Saved. Re-run the QC layers to verify the fixes.")
            st.rerun()
        if c2.button("✖ Discard"):
            st.session_state.pop("proposal")
            st.rerun()
        return

    issues = [*(p.qc1.issues if p.qc1 else []), *(p.qc2.issues if p.qc2 else [])]
    open_issues = [i for i in issues if i.id not in p.applied_issue_ids and i.id not in p.dismissed_issue_ids]
    st.write("Select the recommendations to apply. The AI edits only the affected parts; you review a diff "
             "before anything is saved.")
    if not issues:
        st.info("Run the QC layers to get recommendations. You can still request a custom edit below.")
    selected: list[QCIssue] = []
    for i in sorted(open_issues, key=lambda x: (x.layer, ["critical", "major", "minor"].index(x.severity))):
        c1, c2 = st.columns([12, 1])
        if c1.checkbox(f"{SEV_ICON[i.severity]} **{i.id}** [{i.category}] *{i.location}*: {i.suggestion}",
                       key=f"sel-{p.id}-{i.id}"):
            selected.append(i)
        if c2.button("Dismiss", key=f"dis-{p.id}-{i.id}"):
            p.dismissed_issue_ids.append(i.id)
            store().save(p)
            st.rerun()
    instruction = st.text_area("Additional instruction (optional)", key=f"instr-{p.id}",
                               placeholder="e.g. Use a food-delivery app as the running example")
    if st.button(f"🛠 Generate revision ({len(selected)} selected)", type="primary",
                 disabled=not selected and not instruction.strip()):
        try:
            with st.spinner("Revising the lesson…"):
                result = revise_lesson(p.current_markdown, selected, instruction, p.research,
                                       pipeline().llm, settings())
            st.session_state["proposal"] = {"pid": p.id, "markdown": result.revised_markdown,
                                            "change_log": result.change_log, "ids": [i.id for i in selected]}
            st.rerun()
        except (LLMError, ValueError) as exc:
            st.error(f"{exc} Your lesson was not changed. Press the button again to retry.")
    applied = [i for i in issues if i.id in p.applied_issue_ids]
    if applied:
        st.caption("Already applied: " + ", ".join(i.id for i in applied))


def versions_tab(p: LessonProject) -> None:
    if not p.versions:
        st.info("No versions yet.")
        return
    for v in reversed(p.versions):
        with st.expander(f"v{v.number} · {v.origin} · {v.created_at}" + (" (current)" if v.number == p.current_version else "")):
            if v.note:
                st.caption(v.note)
            st.code(v.markdown[:4000] + ("\n…" if len(v.markdown) > 4000 else ""), language="markdown")
            if v.number != p.current_version and st.button("Restore as new version", key=f"restore-{v.number}"):
                add_version(p, v.markdown, f"restored v{v.number}")
                store().save(p)
                st.rerun()


def export_tab(p: LessonProject) -> None:
    if not p.versions:
        st.info("Nothing to export yet.")
        return
    stale = [n for n, r in (("QC 1", p.qc1), ("QC 2", p.qc2)) if r and r.lesson_version != p.current_version]
    if stale:
        st.warning(f"{', '.join(stale)} audited an older version. Re-run them for an up-to-date export.")
    slug = p.id
    applied = set(p.applied_issue_ids)
    st.download_button("📦 Download everything (ZIP)", build_zip(p), f"{slug}.zip", "application/zip", type="primary")
    c1, c2, c3 = st.columns(3)
    c1.download_button("Lesson (.md)", p.current_markdown, f"{slug}-lesson.md", "text/markdown")
    c1.download_button("Lesson (.html, print to PDF)", to_html(p.current_markdown, p.title),
                       f"{slug}-lesson.html", "text/html")
    c2.download_button("References (.md)", references_markdown(p), f"{slug}-references.md", "text/markdown")
    if p.qc1:
        c3.download_button("QC 1 report (.md)", qc1_markdown(p.qc1, p.title, applied), f"{slug}-qc1.md", "text/markdown")
    if p.qc2:
        c3.download_button("QC 2 report (.md)", qc2_markdown(p.qc2, p.title, applied), f"{slug}-qc2.md", "text/markdown")


def project_page(p: LessonProject) -> None:
    st.header(p.title)
    st.markdown(f"**Learning objective:** {p.objective}")
    pipeline_panel(p)
    st.divider()
    tabs = st.tabs(["🔎 Research", "✏️ Edit", "👁 Preview", "🧪 QC 1: Facts", "🎓 QC 2: Instruction",
                    "🛠 Apply QC fixes", "🕓 Versions", "⬇️ Export"])
    for tab, fn in zip(tabs, (research_tab, editor_tab, preview_tab, qc1_tab, qc2_tab, apply_tab,
                              versions_tab, export_tab)):
        with tab:
            fn(p)
    with st.expander("Danger zone"):
        if st.button("Delete this lesson project"):
            store().delete(p.id)
            st.session_state.pop("pid", None)
            st.rerun()


def main() -> None:
    sidebar()
    p = load_project()
    if p is None:
        new_lesson_page()
    else:
        project_page(p)


main()
