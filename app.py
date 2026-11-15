import shutil
import streamlit as st
import pandas as pd
import psutil
import os
import gc
import time
import ollama
import streamlit.components.v1 as components

# Import our custom modules
# --- CUSTOM MODULE IMPORTS ---
from utils import (
    send_telegram_ping, 
    send_telegram_photo, 
    get_camera_settings, 
    get_jpeg_files, 
    encode_image, 
    save_settings, 
    load_settings
)
from ai_engine import analyze_image, categorize_photo

GLOBAL_LEDGER_PATH = r"C:\Users\aloha\OneDrive\Apps\Codes\image_culling_tool\Hippocampus_Global_Success_Ledger.csv"

def purge_system_memory():
    """Forces Ollama and Python to immediately release RAM and GPU/XPU caches."""
    # 1. Instruct Ollama to evict model weights from RAM/VRAM immediately
    try:
        ollama.generate(model='llava-phi3', prompt='', keep_alive=0)
    except Exception as e:
        print(f"Ollama unload notification: {e}")

    # 2. Force Python garbage collection on all 3 generations
    gc.collect()

    # 3. Release hardware acceleration cache if torch/XPU/CUDA is loaded
    try:
        import torch
        if hasattr(torch, 'xpu') and torch.xpu.is_available():
            torch.xpu.empty_cache()
        elif torch.cuda.is_available():
            torch.cuda.empty_cache()
    except ImportError:
        pass

# --- CONFIGURATION & UI ---
st.set_page_config(page_title="Hippocampus 1.0.0: Live Sync", page_icon="🦛", layout="wide")

st.markdown("""
    <style>
    [data-testid='stSidebar'] { min-width: 350px; }
    div[data-testid="stMetricValue"] {
        background-color: #002b36; color: #268bd2; padding: 15px;
        border-radius: 8px; border: 2px solid #268bd2; font-weight: bold;
    }
    div[data-testid="stMetricLabel"] {
        color: #073642; font-size: 1.1rem; font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

# --- CALIBRATION POPUP ---
@st.dialog("🎯 Calibration Analysis & Strategy")
def calibration_popup(cal_df):
    success_types = ['Keeper_Masterpiece', 'Keeper_Storyteller', 'Keeper_Mood', 'Keeper_Technical', 'Keeper_Maverick']
    elite_df = cal_df[cal_df['AI Category'].isin(success_types)]
    if elite_df.empty: elite_df = cal_df

    avg_s = int(elite_df['Sharpness'].mean())
    avg_crea = int(elite_df['Creativity'].mean()) if 'Creativity' in elite_df.columns else 50
    avg_style = int(elite_df['Style'].mean()) if 'Style' in elite_df.columns else 50
    avg_moleitou = int(elite_df['Mo Lei Tou'].mean()) if 'Mo Lei Tou' in elite_df.columns else 75
   
    st.write(f"**Target Averages:** Sharpness: {avg_s} | Creativity: {avg_crea} | Style: {avg_style} | Mo Lei Tou: {avg_moleitou}")
    if st.button("✅ Sync Thresholds", width='stretch'):
        st.session_state.update(sl_crea=avg_crea, sl_style=avg_style, sl_moleitou=avg_moleitou, calibration_completed=False)
        st.rerun()

# --- STATE & SETTINGS INITIALIZATION ---
if 'is_running' not in st.session_state: st.session_state.is_running = False
if 'last_exec_time' not in st.session_state: st.session_state.last_exec_time = "0m 0s"
if 'session_batch_count' not in st.session_state: st.session_state.session_batch_count = 0
if 'calibration_completed' not in st.session_state: st.session_state.calibration_completed = False

# Default Settings including Last Folder Memory
default_vals = {
    "sharpness": 70, "exposure": 60, "composition": 60, 
    "narrative": 70, "emotional": 60, "keeper": 71, 
    "creativity": 50, "style": 50, "moleitou": 75,
    "last_folder": r"C:\Users\aloha\TestPhotos"
}
saved = load_settings(default_vals)

# Folder Session Sync
if 'last_folder' not in st.session_state:
    st.session_state['last_folder'] = saved.get('last_folder', r"C:\Users\aloha\TestPhotos")

slider_keys = [
    ('sl_sharp', 'sharpness'), ('sl_exp', 'exposure'), ('sl_comp', 'composition'), 
    ('sl_narr', 'narrative'), ('sl_emo', 'emotional'), ('sl_keeper', 'keeper'), 
    ('sl_crea', 'creativity'), ('sl_style', 'style'), ('sl_moleitou', 'moleitou')
]
for k, v in slider_keys:
    if k not in st.session_state: st.session_state[k] = saved.get(v, default_vals.get(v, 50))

# --- SIDEBAR: COMMAND CENTER ---
with st.sidebar:
    st.header("🎛️ Command Center")
    st.divider()
    is_locked = st.session_state.is_running
    
    # 📁 Source Folder with Persistent Memory
    folder_path = st.text_input("📁 Source Folder:", value=st.session_state['last_folder'], disabled=is_locked)
    st.session_state['last_folder'] = folder_path

    op_mode = st.radio("🛠️ System Mode:", ["Operation (My Work)", "Calibration (Pro Benchmarks)"], disabled=is_locked)
    
    # Anchor the Stop button in Sidebar during analysis
    if is_locked:
        if st.button("🛑 EMERGENCY HALT", type="primary", width='stretch'):
            st.session_state.is_running = False
            purge_system_memory()  # 🧹 Immediately evicts model and cleans RAM
            st.rerun()

    st.divider()
    st.subheader("🎯 Quantitative Thresholds")
    c1, c2 = st.columns(2)
    min_sharp = c1.slider("Sharpness", 0, 100, key='sl_sharp', disabled=is_locked)
    min_exp = c2.slider("Exposure", 0, 100, key='sl_exp', disabled=is_locked)
    min_comp = c1.slider("Composition", 0, 100, key='sl_comp', disabled=is_locked)
    keeper_threshold = c2.slider("Min Tech Score", 0, 100, key='sl_keeper', disabled=is_locked)
    
    st.divider()
    st.subheader("🎨 Aesthetic Thresholds")
    c1, c2 = st.columns(2)
    min_narrative = c1.slider("Narrative", 0, 100, key='sl_narr', disabled=is_locked)
    min_emotional = c2.slider("Emotional", 0, 100, key='sl_emo', disabled=is_locked)
    min_creativity = c1.slider("Creativity", 0, 100, key='sl_crea', disabled=is_locked)
    min_style = c2.slider("Style", 0, 100, key='sl_style', disabled=is_locked)
    
    # Stephen Chow Mo Lei Tou Absurdity Slider
    min_moleitou = st.slider("🎭 Mo Lei Tou (Absurdity)", 0, 100, key='sl_moleitou', disabled=is_locked)

    if st.button("💾 Save as Default", width='stretch'):
        save_settings({
            "sharpness": min_sharp, "exposure": min_exp, "composition": min_comp, "keeper": keeper_threshold,
            "narrative": min_narrative, "emotional": min_emotional, "creativity": min_creativity, 
            "style": min_style, "moleitou": min_moleitou,
            "last_folder": st.session_state['last_folder']
        })
        st.success("Global Strategy & Folder Saved!")

    st.divider()
    st.subheader("📡 System Health")
    if st.button("📨 Test Telegram Connection", width='stretch'):
        success = send_telegram_ping("🦛 *Hippocampus Online* Connection Successful! 🚀")
        if success: st.success("Telegram Connected!")
        else: st.error("Connection Failed.")
    st.caption(f"Status: {'Active Scan' if is_locked else 'System Idle'}")

# --- MAIN ENGINE ---
st.title(f"🦛 Hippocampus: {op_mode}")

v_col1, v_col2, v_col3 = st.columns(3)
cpu_meter = v_col1.empty()
ram_meter = v_col2.empty()
timer_meter = v_col3.empty()
cpu_meter.metric("CPU Load", f"{psutil.cpu_percent()}%")
ram_meter.metric("RAM Usage", f"{psutil.virtual_memory().percent}%")
timer_meter.metric("⏱️ Timer", st.session_state.last_exec_time)

if folder_path and os.path.isdir(folder_path):
    report_path = os.path.join(folder_path, "_Hippocampus_Grand_Master_Report.csv")
    files = get_jpeg_files(folder_path)
    
    if os.path.exists(report_path):
        master_df = pd.read_csv(report_path)
        processed = set(master_df[master_df['Mode'] == op_mode]['Filename'].tolist())
    else:
        master_df = pd.DataFrame(columns=["Filename", "Mode", "AI Category", "Sharpness", "Exposure", "Composition", "Tech Score", "Narrative Score", "Emotional Impact", "Creativity", "Style", "Mo Lei Tou", "Focal Length", "Aperture"])
        processed = set()

    files_to_process = [f for f in files if f not in processed]

    # --- ACTION BUTTONS ---
    c1, c2 = st.columns(2)
    if not st.session_state.is_running:
        st.write(f"📂 **Total Found:** {len(files)} | **Remaining:** {len(files_to_process)}")
        if c1.button("🚀 INITIATE ANALYSIS", type="primary", width='stretch') and files_to_process:
            # Auto-save folder path on scan launch
            cfg = load_settings(default_vals)
            cfg['last_folder'] = folder_path
            save_settings(cfg)

            st.session_state.update(is_running=True, session_start=time.time(), session_batch_count=0)
            st.rerun()
        if c2.button("🔄 RE-SYNC CATEGORIES", width='stretch') and not master_df.empty:
            with st.spinner("Applying new thresholds & Mo Lei Tou filters..."):
                for idx, row in master_df.iterrows():
                    m = {k: row.get(k, 0) for k in [
                        'Sharpness', 'Exposure', 'Composition', 'Tech Score', 
                        'Narrative Score', 'Emotional Impact', 'Creativity', 'Style', 'Mo Lei Tou'
                    ]}
                    m['Competition Status'] = row.get('Competition Status', 'PASS')
                    master_df.at[idx, 'AI Category'] = categorize_photo(
                        m, min_sharp, min_exp, min_comp, keeper_threshold, 
                        min_narrative, min_emotional, min_creativity, min_style, min_moleitou
                    )
        
                # 1. Update local Grand Master Report
                master_df.to_csv(report_path, index=False)
        
                # 2. Re-sync Global Success Ledger
                if os.path.exists(GLOBAL_LEDGER_PATH):
                    g_df = pd.read_csv(GLOBAL_LEDGER_PATH)
                    # Remove existing records from this folder/batch, then re-insert current qualifying keepers
                    current_filenames = set(master_df['Filename'].tolist())
                    g_df = g_df[~g_df['Filename'].isin(current_filenames)]
            
                    qualifying_keepers = master_df[master_df['Tech Score'] >= keeper_threshold]
                    if not qualifying_keepers.empty:
                        g_df = pd.concat([g_df, qualifying_keepers], ignore_index=True).drop_duplicates(subset=['Filename'], keep='last')
            
                    g_df.to_csv(GLOBAL_LEDGER_PATH, index=False)

                st.session_state.session_batch_count += 1
                st.success("Re-Synced Local & Global Ledgers!")
                st.rerun()
    else:
        if st.button("🛑 STOP ANALYSIS", type="primary", key="main_stop_btn", width='stretch'):
            st.session_state.is_running = False
            purge_system_memory()  # 🧹 Immediately evicts model and cleans RAM
            st.rerun()

    # --- SCAN LOOP WITH 10-FRAME CHAMPION SPOTLIGHT ---
    if st.session_state.is_running:
        st.subheader("⚡ Live Analysis & Batch Spotlight")
        
        # Dedicated UI containers for progress and the 10-frame Champion Spotlight
        spotlight_box = st.empty()
        status_text = st.empty()
        progress = st.progress(0)

        # Buffer to track the current 10-frame window
        current_batch_records = []
        batch_counter = 0

        def process_and_broadcast_champion(records, batch_num):
            """Identifies the best frame in the 10-pack, spotlights it in UI, and pings Telegram."""
            if not records:
                return

            # Documentary Composite Score: Balances Technical Execution with Soul & Story
            best_record = max(
                records,
                key=lambda r: (
                    r.get('Tech Score', 0) * 0.40 + 
                    r.get('Narrative Score', 0) * 0.30 + 
                    r.get('Emotional Impact', 0) * 0.30
                )
            )

            best_file = best_record['Filename']
            best_img_path = os.path.join(folder_path, best_file)

            # 1. Render in Streamlit Live Interface
            with spotlight_box.container():
                st.markdown(f"#### 🏆 **Batch #{batch_num} Champion:** `{best_file}`")
                c_img, c_meta = st.columns([1, 1.2])
                with c_img:
                    if os.path.isfile(best_img_path):
                        from PIL import Image, ImageOps
                        with Image.open(best_img_path) as b_img:
                            st.image(ImageOps.exif_transpose(b_img), use_container_width=True)
                with c_meta:
                    st.markdown(f"**Tier:** `{best_record.get('AI Category')}` | **Lens:** `{best_record.get('Focal Length')} @ {best_record.get('Aperture')}`")
                    sc1, sc2, sc3 = st.columns(3)
                    sc1.metric("Tech Score", best_record.get('Tech Score', 0))
                    sc2.metric("Narrative", best_record.get('Narrative Score', 0))
                    sc3.metric("Emotion", best_record.get('Emotional Impact', 0))
                    st.info(f"**Curator Remark:**\n\n{best_record.get('Raw Reply', 'N/A')}")

            # 2. Transmit to Telegram (Formatted with HTML tags)
            critique_clean = best_record.get('Raw Reply', '').replace('**', '').replace('📖', '').replace('🎨', '')
            
            tg_caption = (
                f"🏆 <b>[BATCH #{batch_num} CHAMPION]</b>\n"
                f"📁 <code>{best_file}</code>\n"
                f"🏷️ Tier: <b>{best_record.get('AI Category')}</b>\n"
                f"📷 <code>{best_record.get('Focal Length')} | {best_record.get('Aperture')}</code>\n"
                f"────────────────────────\n"
                f"🛠️ Tech: <b>{best_record.get('Tech Score')}</b> | 📐 Comp: <b>{best_record.get('Composition')}</b> | 🔍 Sharp: <b>{best_record.get('Sharpness')}</b>\n"
                f"📖 Narrative: <b>{best_record.get('Narrative Score')}</b> | 🎭 Emotion: <b>{best_record.get('Emotional Impact')}</b>\n"
                f"🃏 Mo Lei Tou: <b>{best_record.get('Mo Lei Tou')}</b> | ☕ Roast: <b>{best_record.get('Chinny Roast')}/100</b>\n"
                f"────────────────────────\n"
                f"📝 <b>Curator Remarks:</b>\n<i>{critique_clean[:500]}</i>"
            )

            if os.path.isfile(best_img_path):
                send_telegram_photo(best_img_path, tg_caption)

        try:
            for i, f in enumerate(files_to_process):
                if not st.session_state.is_running:
                    break

                filepath = os.path.join(folder_path, f)
                status_text.text(f"Scanning {f}... ({i+1}/{len(files_to_process)})")

                # Image Encoding
                encoded_img = encode_image(filepath)
                if encoded_img is None:
                    continue

                # AI Analysis
                metrics = analyze_image(encoded_img, op_mode)
                if metrics is None:
                    status_text.text(f"⚠️ Warning: Ollama skipped {f}, retrying next...")
                    continue

                cat = categorize_photo(
                    metrics, min_sharp, min_exp, min_comp, keeper_threshold, 
                    min_narrative, min_emotional, min_creativity, min_style, min_moleitou
                )
                focal, ap = get_camera_settings(filepath)

                row_dict = {
                    **metrics, 
                    "Filename": f, 
                    "Mode": op_mode, 
                    "AI Category": cat, 
                    "Focal Length": focal, 
                    "Aperture": ap
                }
                new_row = pd.DataFrame([row_dict])

                # Immediate Disk Flush
                master_df = pd.concat([master_df, new_row], ignore_index=True).drop_duplicates(subset=['Filename', 'Mode'], keep='last')
                master_df.to_csv(report_path, index=False)

                # Keepers Ledger Update
                if metrics.get('Tech Score', 0) >= keeper_threshold:
                    os.makedirs(os.path.dirname(GLOBAL_LEDGER_PATH), exist_ok=True)
                    g_df = pd.read_csv(GLOBAL_LEDGER_PATH) if os.path.exists(GLOBAL_LEDGER_PATH) else pd.DataFrame()
                    pd.concat([g_df, new_row], ignore_index=True).drop_duplicates(subset=['Filename'], keep='last').to_csv(GLOBAL_LEDGER_PATH, index=False)

                # Add to rolling 10-frame buffer
                current_batch_records.append(row_dict)
                st.session_state.session_batch_count += 1
                progress.progress((i + 1) / len(files_to_process))

                elapsed = time.time() - st.session_state.session_start
                st.session_state.last_exec_time = f"{int(elapsed // 60)}m {int(elapsed % 60)}s"
                timer_meter.metric("⏱️ Timer", st.session_state.last_exec_time)

                # Check if 10-frame batch threshold reached
                if len(current_batch_records) == 10:
                    batch_counter += 1
                    process_and_broadcast_champion(current_batch_records, batch_counter)
                    current_batch_records = []  # Reset buffer for next 10

                # Memory Clean
                if (i + 1) % 10 == 0:
                    gc.collect()
                    purge_system_memory()

            # Process any remaining photos (e.g., last batch of 4 or 7 photos)
            if current_batch_records:
                batch_counter += 1
                process_and_broadcast_champion(current_batch_records, f"{batch_counter} (Final)")

        except Exception as err:
            st.error(f"⚠️ Scan interrupted: {err}")
            print(f"Scan Loop Error: {err}")

        finally:
            st.session_state.is_running = False
            st.rerun()

    # --- DASHBOARD (TACTICAL INTELLIGENCE) ---
    st.divider()
    df_dash = master_df[master_df['Mode'] == op_mode] if not master_df.empty else pd.DataFrame()

    st.subheader(f"📊 Tactical Performance: {op_mode}")

    if not df_dash.empty:
        # 1. 🛡️ ALERTS & FLAGS RIBBON
        dq_count = len(df_dash[df_dash['Competition Status'] == 'DQ'])
        privacy_count = len(df_dash[df_dash['Privacy Alert'].str.upper() == 'YES']) if 'Privacy Alert' in df_dash.columns else 0

        if dq_count > 0 or privacy_count > 0:
            a_col1, a_col2 = st.columns(2)
            if dq_count > 0:
                a_col1.error(f"🚨 **Disqualified for Competition:** {dq_count} photos flagged")
            if privacy_count > 0:
                a_col2.warning(f"🔒 **Privacy Alerts Triggered:** {privacy_count} photos contain sensitive data")

        # 2. 🏛️ CORE TECHNICAL & COMPOSITION PILLARS
        st.markdown("### 📐 **Technical & Compositional Foundation**")
        tech_cols = st.columns(4)
        avg_comp = df_dash['Composition'].mean() if 'Composition' in df_dash.columns else 0
        avg_sharp = df_dash['Sharpness'].mean() if 'Sharpness' in df_dash.columns else 0
        avg_exp = df_dash['Exposure'].mean() if 'Exposure' in df_dash.columns else 0
        avg_tech = df_dash['Tech Score'].mean() if 'Tech Score' in df_dash.columns else 0

        tech_cols[0].metric("📐 Avg Composition (45%)", f"{avg_comp:.1f}")
        tech_cols[1].metric("🔍 Avg Sharpness (35%)", f"{avg_sharp:.1f}")
        tech_cols[2].metric("☀️ Avg Exposure (20%)", f"{avg_exp:.1f}")
        tech_cols[3].metric("🛠️ Combined Tech Score", f"{avg_tech:.1f}")

        # 3. 🎨 AESTHETICS, SOUL & MO LEI TOU
        st.markdown("### 🏹 **Aesthetic, Story & Satire**")
        soul_cols = st.columns(5)
        avg_narr = df_dash['Narrative Score'].mean() if 'Narrative Score' in df_dash.columns else 0
        avg_emo = df_dash['Emotional Impact'].mean() if 'Emotional Impact' in df_dash.columns else 0
        avg_crea = df_dash['Creativity'].mean() if 'Creativity' in df_dash.columns else 0
        avg_style = df_dash['Style'].mean() if 'Style' in df_dash.columns else 0
        avg_moleitou = df_dash['Mo Lei Tou'].mean() if 'Mo Lei Tou' in df_dash.columns else 0

        soul_cols[0].metric("📖 Narrative", f"{avg_narr:.1f}")
        soul_cols[1].metric("🎭 Emotional", f"{avg_emo:.1f}")
        soul_cols[2].metric("💡 Creativity", f"{avg_crea:.1f}")
        soul_cols[3].metric("✨ Style", f"{avg_style:.1f}")
        soul_cols[4].metric("🃏 Mo Lei Tou", f"{avg_moleitou:.1f}")

        st.divider()

        # 4. 🏛️ CATEGORY DISTRIBUTION
        total_scanned = len(df_dash)
        st.markdown(f"### 🗂️ **Category Breakdown ({total_scanned} Photos)**")
        m_cols = st.columns(7)
        cats = ['Keeper_Masterpiece', 'Keeper_Storyteller', 'Keeper_Maverick', 'Keeper_Mood', 'Keeper_Technical', 'Review', 'Discard']
        labels = ["🌟 Master", "📖 Story", "⚡ Maverick", "🎭 Mood", "⚙️ Tech", "🕶️ Review", "🗑️ Discard"]

        for i, c_name in enumerate(cats):
            count = len(df_dash[df_dash['AI Category'] == c_name])
            m_cols[i].metric(labels[i], count)

        st.divider()

        # 5. 📋 MASTER TELEMETRY TABLE (All Columns Displayed)
        st.markdown("### 🧾 **Complete Telemetry Ledger**")
        
        # Order columns logically: Identification -> Category -> Scores -> Special Flags -> Gear
        all_ordered_cols = [
            'Filename', 'AI Category', 'Tech Score', 'Composition', 'Sharpness', 
            'Exposure', 'Narrative Score', 'Emotional Impact', 'Creativity', 'Style', 
            'Mo Lei Tou', 'Chinny Roast', 'Competition Status', 'Privacy Alert', 
            'Focal Length', 'Aperture'
        ]
        active_cols = [c for c in all_ordered_cols if c in df_dash.columns]

        st.dataframe(
            df_dash[active_cols],
            width='stretch',
            column_config={
                "Tech Score": st.column_config.ProgressColumn("Tech Score", min_value=0, max_value=100, format="%d"),
                "Composition": st.column_config.NumberColumn("Composition", format="%d"),
                "Competition Status": st.column_config.TextColumn("Comp Status"),
                "Privacy Alert": st.column_config.TextColumn("Privacy"),
            },
            hide_index=True
        )

        # 6. 🔍 CURATOR'S DEEP-DIVE INSPECTOR (STABLE CALLBACK ENGINE)
        if 'Raw Reply' in df_dash.columns:
            st.markdown("### 🧐 **Curator Critique & Visual Inspector**")

            file_options = df_dash['Filename'].tolist()
            total_photos = len(file_options)

            # --- 1. STATE INITIALIZATION ---
            if 'inspector_idx' not in st.session_state:
                st.session_state.inspector_idx = 0
            if 'inspector_select' not in st.session_state:
                st.session_state.inspector_select = file_options[st.session_state.inspector_idx]

            # Boundary guard
            if st.session_state.inspector_idx >= total_photos:
                st.session_state.inspector_idx = 0
                st.session_state.inspector_select = file_options[0]

            # --- 2. SYNCHRONOUS CALLBACK HANDLERS ---
            def nav_prev():
                st.session_state.inspector_idx = (st.session_state.inspector_idx - 1) % total_photos
                st.session_state.inspector_select = file_options[st.session_state.inspector_idx]

            def nav_next():
                st.session_state.inspector_idx = (st.session_state.inspector_idx + 1) % total_photos
                st.session_state.inspector_select = file_options[st.session_state.inspector_idx]

            def on_dropdown_change():
                chosen = st.session_state.inspector_select
                if chosen in file_options:
                    st.session_state.inspector_idx = file_options.index(chosen)

            # --- 3. KEYBOARD SHORTCUT LISTENER (← / →) ---
            components.html(
                """
                <script>
                const parentDoc = window.parent.document;
                if (!parentDoc._hippo_keys_attached) {
                    parentDoc._hippo_keys_attached = true;
                    parentDoc.addEventListener('keydown', function(event) {
                        const activeTag = parentDoc.activeElement ? parentDoc.activeElement.tagName.toLowerCase() : '';
                        if (activeTag === 'input' || activeTag === 'textarea') return;

                        if (event.key === 'ArrowLeft') {
                            const btn = Array.from(parentDoc.querySelectorAll('button')).find(b => b.innerText.includes('Prev'));
                            if (btn) btn.click();
                        } else if (event.key === 'ArrowRight') {
                            const btn = Array.from(parentDoc.querySelectorAll('button')).find(b => b.innerText.includes('Next'));
                            if (btn) btn.click();
                        }
                    });
                }
                </script>
                """,
                height=0,
                width=0
            )

            # --- 4. NAVIGATION BAR (ZERO-LOCK CALLBACKS) ---
            col_prev, col_select, col_next = st.columns([1, 3, 1])

            with col_prev:
                st.button("⬅️ Prev (←)", key="btn_inspect_prev", on_click=nav_prev, use_container_width=True)

            with col_next:
                st.button("Next ➡️ (→)", key="btn_inspect_next", on_click=nav_next, use_container_width=True)

            with col_select:
                selected_file = st.selectbox(
                    label="Active Photograph",
                    options=file_options,
                    key="inspector_select",
                    on_change=on_dropdown_change,
                    label_visibility="collapsed"
                )

            # --- 5. DUAL-PANE INSPECTION DISPLAY ---
            if selected_file:
                selected_row = df_dash[df_dash['Filename'] == selected_file].iloc[0]

                # Dynamic path resolution across all tier directories
                target_subdirs = [
                    "", "1_Masterpiece", "2_Storyteller", "3_Mood", 
                    "4_Technical", "5_Maverick", "Review_Needed", "Discarded"
                ]
                img_path = None
                for sub in target_subdirs:
                    candidate = os.path.join(folder_path, sub, selected_file)
                    if os.path.isfile(candidate):
                        img_path = candidate
                        break

                col_img, col_critique = st.columns([1.1, 1.2])

                with col_img:
                    if img_path and os.path.isfile(img_path):
                        from PIL import Image, ImageOps
                        try:
                            with Image.open(img_path) as src_img:
                                # 1. Auto-orient via EXIF
                                display_img = ImageOps.exif_transpose(src_img)
                                
                                # 2. Downscale for lightning-fast UI rendering (Fixes media server timeouts)
                                display_img.thumbnail((1200, 1200))
                                
                                st.image(
                                    display_img, 
                                    caption=f"{selected_file} [{selected_row.get('AI Category', 'Unassigned')}]", 
                                    use_container_width=True
                                )
                        except Exception as e:
                            st.error(f"Image load failure: {e}")
                    else:
                        st.warning(f"⚠️ Source image file not found on disk: `{selected_file}`")

                with col_critique:
                    st.markdown(f"""
                    **Frame:** `{st.session_state.inspector_idx + 1} / {total_photos}` | 
                    **Category:** `{selected_row.get('AI Category', 'N/A')}` | 
                    **Gear:** `{selected_row.get('Focal Length', 'N/A')}` @ `{selected_row.get('Aperture', 'N/A')}`
                    """)

                    # Score snapshot meters
                    s_col1, s_col2, s_col3 = st.columns(3)
                    s_col1.metric("Tech Score", int(selected_row.get('Tech Score', 0)))
                    s_col2.metric("Narrative", int(selected_row.get('Narrative Score', 0)))
                    s_col3.metric("Emotion", int(selected_row.get('Emotional Impact', 0)))

                    # AI Curator Written Critique
                    st.info(f"**Curator's Assessment:**\n\n{selected_row.get('Raw Reply', 'No critique available.')}")

                    # Flavor flags
                    roast_val = int(selected_row.get('Chinny Roast', 0))
                    comp_stat = str(selected_row.get('Competition Status', 'PASS')).upper()
                    st.caption(f"☕ **Chinny Roast:** {roast_val}/100 | 🏆 **Comp Status:** `{comp_stat}`")

        # 7. PHYSICAL DEPLOY ROUTER
        if not st.session_state.is_running and st.button("🏗️ PHYSICAL DEPLOY / RE-SORT", width='stretch'):
            cmap = {
                "Keeper_Masterpiece": "1_Masterpiece", 
                "Keeper_Storyteller": "2_Storyteller", 
                "Keeper_Mood": "3_Mood", 
                "Keeper_Technical": "4_Technical", 
                "Keeper_Maverick": "5_Maverick", 
                "Review": "Review_Needed", 
                "Discard": "Discarded"
            }
            
            # 1. Ensure all destination subdirectories exist
            for folder_name in cmap.values(): 
                os.makedirs(os.path.join(folder_path, folder_name), exist_ok=True)
            
            # Search pool: root folder + every possible category subfolder
            search_dirs = [folder_path] + [os.path.join(folder_path, d) for d in cmap.values()]
            
            moved_count = 0
            already_in_place = 0
            missing_count = 0
            
            with st.spinner("Re-routing files across category folders..."):
                for _, r in df_dash.iterrows():
                    fname = r['Filename']
                    target_dir_name = cmap.get(r['AI Category'], 'Review_Needed')
                    dest_path = os.path.join(folder_path, target_dir_name, fname)
                    
                    # 2. Locate the file's current physical position
                    current_path = None
                    for d in search_dirs:
                        candidate = os.path.join(d, fname)
                        if os.path.isfile(candidate):
                            current_path = candidate
                            break
                    
                    # 3. Route according to status
                    if current_path is None:
                        missing_count += 1
                        continue
                    
                    # If already in the correct folder, skip the operation
                    if os.path.normpath(current_path) == os.path.normpath(dest_path):
                        already_in_place += 1
                        continue
                    
                    try:
                        shutil.move(current_path, dest_path)
                        moved_count += 1
                    except Exception as err:
                        st.error(f"Failed to move {fname}: {err}")
            
            # 4. Telemetry output
            st.success(f"🏁 Re-sort Complete! Re-routed: **{moved_count}** photos | Retained in place: **{already_in_place}**")
            if missing_count > 0:
                st.warning(f"⚠️ {missing_count} photos in the report could not be found on disk.")

# --- HABITS (Global Ledger) ---
st.divider()
if os.path.exists(GLOBAL_LEDGER_PATH):
    st.subheader("🏆 Global Success Habits")
    g_df = pd.read_csv(GLOBAL_LEDGER_PATH)
    succ_df = g_df[g_df['AI Category'].str.contains('Keeper', na=False)] if not g_df.empty else pd.DataFrame()
    if not succ_df.empty:
        c1, c2 = st.columns(2)
        c1.bar_chart(succ_df['Focal Length'].value_counts())
        c2.bar_chart(succ_df['Aperture'].value_counts())