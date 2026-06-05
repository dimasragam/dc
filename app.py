import streamlit as st # type: ignore


##################################################################
### Configure App
### st.set_page_config HARUS ada di app.py, bukan di page1.py
### Hapus st.set_page_config() dari page1.py setelah ini jalan
##################################################################

st.set_page_config(
    page_title="Always Healthy Hospital Performance",
    page_icon="🏥",
    layout="wide",
)


##################################################################
### CSS — Sidebar Styling
### Mengatur tampilan sidebar agar menyerupai foto referensi:
### background putih #FBFBFD, active nav item hijau #BCF29E
##################################################################

st.markdown("""
<style>

    /* ── Background sidebar ─────────────────────────── */
    section[data-testid="stSidebar"] {
        background-color: #edf5ea !important;
        border-right: 1px solid #e8e8ed !important;
    }

    /* ── Logo / judul di atas sidebar ───────────────── */
    section[data-testid="stSidebar"] .st-emotion-cache-1cypcdb {
        padding-top: 1.5rem;
    }
    
    /* ── Semua nav link (menu item) ─────────────────── */
    [data-testid="stSidebarNavLink"] {
        border-radius: 10px !important;
        margin: 2px 8px !important;
        padding: 10px 14px !important;
        color: #374151 !important;
        font-weight: 500 !important;
        font-size: 0.9rem !important;
        transition: background-color 0.15s ease !important;
        text-decoration: none !important;
    }

    [data-testid="stSidebarNavLink"][aria-current="page"] {
    background-color: #BCF29E !important;
    color: #1a4d2e !important;
    font-weight: 600 !important;
    border-radius: 20px !important;   /* ← naikkan dari 10px */
    }

    /* Samakan juga border-radius untuk semua nav link agar konsisten */
    [data-testid="stSidebarNavLink"] {
        border-radius: 20px !important;
    }

    /* ── Hover state — hijau muda ────────────────────── */
    [data-testid="stSidebarNavLink"]:hover {
        background-color: #e6fcd8 !important;
        color: #1a6b2f !important;
    }

    /* ── Active / selected menu item — hijau #BCF29E ── */
    [data-testid="stSidebarNavLink"][aria-current="page"] {
        background-color: #BCF29E !important;
        color: #1a4d2e !important;
        font-weight: 600 !important;
    }

    /* ── Sembunyikan garis default navigasi streamlit ── */
    [data-testid="stSidebarNav"] {
        padding-top: 0.5rem;
    }

    /* ── Teks sidebar (filter, caption) ─────────────── */
    section[data-testid="stSidebar"] * {
        color: #374151;
    }

    /* ── Caption di bawah sidebar ───────────────────── */
    section[data-testid="stSidebar"] .stCaption {
        color: #9ca3af !important;
        font-size: 0.75rem !important;
    }

    .stMainBlockContainer {
        padding-top: 1rem !important;
    }

    /* Hilangkan background merah pada selected tag multiselect */
    [data-testid="stMultiSelectChip"] {
        background-color: #ffffff !important;
        border: 1px solid #d1d5db !important;
        color: #374151 !important;
        border-radius: 6px !important;
    }

    /* Tombol X pada tag */
    [data-testid="stMultiSelectChipClose"] {
        color: #1a1a2e !important;
    }
</style>
""", unsafe_allow_html=True)


##################################################################
### Navigation
### Daftarkan semua page di sini.
### default=True → halaman yang pertama muncul saat web dibuka.
### Letakkan file page di dalam folder pages/
##################################################################

pg = st.navigation(
    [
        st.Page(
            "pages/page1.py",
            title="Overview",
            icon=":material/dashboard:",
            default=True,
        ),
        st.Page(
            "pages/page2.py",
            title="Touchpoint Performance",
            icon=":material/science:",
        ),
    ]
)

pg.run()


##################################################################
### Sidebar Branding
### Konten ini muncul di SEMUA halaman secara konsisten
##################################################################

with st.sidebar:
    st.divider()
    st.caption("Always Healthy Hospital © 2025")