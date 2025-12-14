import streamlit as st
from datetime import datetime

# ページ設定
st.set_page_config(
    page_title="ゲーム最適感度",
    page_icon="🎮",
    layout="wide",
)

# =============================
#  感度診断ロジック
# =============================

def get_game_mid_edpi(game_name: str) -> float:
    """ゲームごとの平均的な mid eDPI（目安）"""
    name = game_name.lower()

    if "valorant" in name:
        return 262.0  # 800dpi × 0.328 ≒ 262（あなた基準）
    if "apex" in name:
        return 1100.0
    if "fortnite" in name:
        return 80.0
    if "overwatch" in name:
        return 1000.0
    if "call of duty" in name or "cod" in name or "warzone" in name:
        return 800.0
    if "league of legends" in name or "lol" in name:
        return 2400.0
    if "minecraft" in name:
        return 360.0
    return 1000.0  # その他


def build_base_edpi(game_name: str):
    """mid（平均）から low/mid/high の eDPI 目安を自動生成"""
    mid = get_game_mid_edpi(game_name)
    return {"low": mid / 2.0, "mid": mid, "high": mid * 1.5}


def classify_style(edpi: float, base_edpi: dict):
    """最終 eDPI がロー/ミドル/ハイのどこに近いか（参考表示）"""
    diffs = {style: abs(edpi - val) for style, val in base_edpi.items()}
    best_style = min(diffs, key=diffs.get)

    label = {
        "low": "ローセンシ寄り",
        "mid": "ミドルセンシ（平均）寄り",
        "high": "ハイセンシ寄り",
    }[best_style]

    return best_style, label


def ab_step(base_sens: float, dpi: int, choice: str):
    """
    1回分のA/B/M選択から、次の基準感度と履歴用の情報を返す。
    ・候補A = base_sens * 0.75
    ・候補B = base_sens * 1.25
    """
    low_sens = base_sens * 0.75
    high_sens = base_sens * 1.25
    low_edpi = low_sens * dpi
    high_edpi = high_sens * dpi

    if choice == "A":
        chosen = low_sens
        other = base_sens
    elif choice == "B":
        chosen = high_sens
        other = base_sens
    else:
        middle = (low_sens + high_sens) / 2.0
        chosen = base_sens
        other = middle

    next_base = (chosen + other) / 2.0
    return next_base, {
        "base_sens": base_sens,
        "low_sens": low_sens,
        "high_sens": high_sens,
        "choice": choice,
    }


def choice_label_jp(choice: str) -> str:
    if choice == "A":
        return "A（ロー寄り）"
    if choice == "B":
        return "B（ハイ寄り）"
    return "M（どちらも微妙）"


def style_label_jp(style_key: str) -> str:
    return {"low": "ローセンシ", "mid": "ミドルセンシ（平均）", "high": "ハイセンシ"}.get(
        style_key, style_key
    )


def log_result_to_file(
    dpi,
    game_name,
    base_edpi,
    current_style,
    target_style,
    final_edpi,
    final_sens,
    judged_label,
    history,
    env_info,
    mode_label,
):
    """結果をテキストファイルにも保存"""
    with open("sens_log_app.txt", "a", encoding="utf-8") as f:
        f.write("==== 感度診断ログ（Streamlit版） ====\n")
        f.write(f"日時       : {datetime.now()}\n")
        f.write(f"ゲーム     : {game_name}\n")
        f.write(f"DPI        : {dpi}\n")
        f.write(
            "基準 eDPI  : ロー={:.1f}, ミドル={:.1f}, ハイ={:.1f}\n".format(
                base_edpi["low"], base_edpi["mid"], base_edpi["high"]
            )
        )
        f.write(f"普段スタイル: {current_style}\n")
        f.write(f"調整ターゲット: {target_style}\n")
        f.write(f"モード     : {mode_label}\n")
        f.write("最終 eDPI  : {:.1f}\n".format(final_edpi))
        f.write("最終 感度  : {:.4f}\n".format(final_sens))
        f.write(f"判定スタイル: {judged_label}\n")

        if env_info:
            f.write("-- 環境情報 --\n")
            f.write(f"  室温      : {env_info.get('temp', '')}\n")
            f.write(f"  湿度      : {env_info.get('humid', '')}\n")
            f.write(f"  天気      : {env_info.get('weather', '')}\n")
            f.write(f"  時間帯    : {env_info.get('timeband', '')}\n")
            f.write(f"  メモ      : {env_info.get('note', '')}\n")

        f.write("-- 調整履歴 --\n")
        for i, h in enumerate(history, start=1):
            f.write(
                "  ラウンド {round}: 基準感度={base:.4f}, ロー候補={low:.4f}, "
                "ハイ候補={high:.4f}, 選択={choice}\n".format(
                    round=i,
                    base=h["base_sens"],
                    low=h["low_sens"],
                    high=h["high_sens"],
                    choice=choice_label_jp(h["choice"]),
                )
            )
        f.write("\n")


# =============================
#  状態管理 & ダークテーマ
# =============================

def init_state():
    if "page" not in st.session_state:
        st.session_state.page = "setup"  # "setup" / "test" / "result"
    if "step" not in st.session_state:
        st.session_state.step = 0
    if "base_sens" not in st.session_state:
        st.session_state.base_sens = None
    if "history" not in st.session_state:
        st.session_state.history = []
    if "finished" not in st.session_state:
        st.session_state.finished = False
    if "rounds" not in st.session_state:
        st.session_state.rounds = 5
    if "dpi" not in st.session_state:
        st.session_state.dpi = None
    if "game_name" not in st.session_state:
        st.session_state.game_name = None
    if "base_edpi" not in st.session_state:
        st.session_state.base_edpi = None
    if "current_style" not in st.session_state:
        st.session_state.current_style = None
    if "target_style" not in st.session_state:
        st.session_state.target_style = None
    if "mode_label" not in st.session_state:
        st.session_state.mode_label = ""
    if "env_info" not in st.session_state:
        st.session_state.env_info = None
    if "logged_to_file" not in st.session_state:
        st.session_state.logged_to_file = False


def set_dark_style():
    """
    とにかく「黒背景＋白文字＋ボタンが見える」ことを最優先したシンプルなCSS
    """
    st.markdown(
        """
        <style>
        /* 全体の背景と文字色 */
        body, .stApp, .block-container {
            background-color: #050608 !important;
            color: #ffffff !important;
        }

        h1, h2, h3, h4, h5, h6, p, span, label {
            color: #ffffff !important;
        }

        /* ボタンを濃い青＋白文字にする */
        div.stButton > button:first-child {
            background-color: #2563eb !important;
            color: #ffffff !important;
            border-radius: 999px !important;
            padding: 0.6rem 1.6rem !important;
            border: 1px solid #93c5fd !important;
            font-weight: 600 !important;
        }
        div.stButton > button:first-child:hover {
            background-color: #1d4ed8 !important;
            border-color: #bfdbfe !important;
            color: #ffffff !important;
        }

        /* テキスト入力・数値入力・テキストエリア */
        input, textarea {
            background-color: #111827 !important;
            color: #f9fafb !important;
            border: 1px solid #374151 !important;
        }
        input::placeholder, textarea::placeholder {
            color: #9ca3af !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# =============================
#  画面ごとの描画
# =============================

def render_setup_screen():
    st.markdown(
        "<h1>🎮 ゲーム最適感度ドクター</h1>",
        unsafe_allow_html=True,
    )
    st.caption("A/Bテストで、あなたの手に合うゲーム内感度を診断します。")

    st.markdown("## ① 設定 🧩")

    st.subheader("基本設定")

    game_name = st.selectbox(
        "ゲームを選択",
        [
            "Valorant",
            "Apex Legends",
            "Fortnite",
            "Overwatch 2",
            "Call of Duty",
            "League of Legends",
            "Minecraft",
            "Other",
        ],
    )

    dpi = st.number_input(
        "テストするDPI", min_value=100, max_value=6400, value=800, step=50
    )

    style_map = {"ローセンシ": "low", "ミドルセンシ（平均）": "mid", "ハイセンシ": "high"}

    current_style_label = st.selectbox(
        "普段プレイしているスタイル",
        list(style_map.keys()),
        index=1,
    )
    current_style = style_map[current_style_label]

    test_type = st.radio(
        "テストの種類",
        ["普段のスタイルのまま微調整する", "普段とは違うスタイル・感度帯を試す"],
    )

    if test_type == "普段のスタイルのまま微調整する":
        target_style = current_style
    else:
        target_style_label = st.selectbox(
            "今回試してみたいスタイル",
            list(style_map.keys()),
            index=2,
        )
        target_style = style_map[target_style_label]

    mode_label = st.radio(
        "A/Bテスト回数（多いほど細かく調整）",
        ["早く決める（5回）", "中間（6回）", "じっくり（7回）"],
    )

    if mode_label.startswith("早く"):
        rounds = 5
    elif mode_label.startswith("じっくり"):
        rounds = 7
    else:
        rounds = 6

    if test_type == "普段とは違うスタイル・感度帯を試す" and target_style != current_style:
        rounds = 7

    st.subheader("環境情報（任意）🌡")

    env_use = st.radio("その日の環境も一緒に記録しますか？", ["いいえ", "はい"])
    env_info = None
    if env_use == "はい":
        col1, col2 = st.columns(2)
        with col1:
            temp = st.text_input("室温（例：24.5℃）", "")
            weather = st.text_input("天気（例：晴れ / 曇り / 雨）", "")
        with col2:
            humid = st.text_input("湿度（例：50%）", "")
            timeband = st.text_input("プレイ時間帯（例：朝 / 夜）", "")
        note = st.text_area("その他メモ（手の状態・マウスパッドなど）", "")
        env_info = {
            "temp": temp,
            "humid": humid,
            "weather": weather,
            "timeband": timeband,
            "note": note,
        }

    st.markdown("---")

    if st.button("A/B テストを開始する ▶"):
        base_edpi = build_base_edpi(game_name)
        start_edpi = base_edpi[target_style]
        base_sens = start_edpi / dpi

        st.session_state.page = "test"
        st.session_state.step = 1
        st.session_state.base_sens = base_sens
        st.session_state.history = []
        st.session_state.finished = False
        st.session_state.rounds = rounds
        st.session_state.dpi = dpi
        st.session_state.game_name = game_name
        st.session_state.base_edpi = base_edpi
        st.session_state.current_style = current_style
        st.session_state.target_style = target_style
        st.session_state.mode_label = mode_label
        st.session_state.env_info = env_info
        st.session_state.logged_to_file = False

        st.rerun()


def render_test_screen():
    st.markdown("## ② A/Bテストで感度を絞り込み 🎯")

    if st.session_state.finished:
        st.session_state.page = "result"
        st.rerun()
        return

    dpi_s = st.session_state.dpi
    base_edpi = st.session_state.base_edpi
    base_sens = st.session_state.base_sens
    step = st.session_state.step

    st.markdown(
        f"<p>現在の設定：<b>{st.session_state.game_name}</b> / DPI {dpi_s} / "
        f"ターゲット：{style_label_jp(st.session_state.target_style)}</p>",
        unsafe_allow_html=True,
    )

    st.markdown(f"<h3>【第 {step} 回 調整】</h3>", unsafe_allow_html=True)

    low_sens = base_sens * 0.75
    high_sens = base_sens * 1.25
    low_edpi = low_sens * dpi_s
    high_edpi = high_sens * dpi_s

    colA, colB = st.columns(2)

    with colA:
        st.markdown(
            f"""
            <div style="border-radius: 8px; padding: 16px; background-color: #111827;
                        border: 1px solid #374151;">
              <h4>候補A（ロー寄り）</h4>
              <p>DPI {dpi_s} / 感度 <b>{low_sens:.4f}</b><br/>
              eDPI {low_edpi:.1f}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with colB:
        st.markdown(
            f"""
            <div style="border-radius: 8px; padding: 16px; background-color: #111827;
                        border: 1px solid #374151;">
              <h4>候補B（ハイ寄り）</h4>
              <p>DPI {dpi_s} / 感度 <b>{high_sens:.4f}</b><br/>
              eDPI {high_edpi:.1f}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.caption("※ 実際にはゲーム内でAとBを試すイメージで、近い方を選んでください。")

    choice = st.radio(
        "どちらが自分の理想に近いですか？",
        ["A（ロー寄り）", "B（ハイ寄り）", "どちらも微妙"],
        key=f"choice_round_{step}",
    )

    if st.button("この選択で次へ →"):
        if choice.startswith("A"):
            ch = "A"
        elif choice.startswith("B"):
            ch = "B"
        else:
            ch = "M"

        next_base, hist = ab_step(base_sens, dpi_s, ch)
        st.session_state.history.append(hist)
        st.session_state.base_sens = next_base

        if step >= st.session_state.rounds:
            st.session_state.finished = True
            st.session_state.page = "result"
        else:
            st.session_state.step += 1

        st.rerun()

    st.markdown("---")
    st.markdown(
        "<p style='font-size:0.8rem; color:#aaaaaa;'>このDPIでのロー / ミドル / ハイのおおよその目安</p>",
        unsafe_allow_html=True,
    )

    cols = st.columns(3)
    labels = {"low": "ロー", "mid": "ミドル（平均）", "high": "ハイ"}
    for i, style in enumerate(["low", "mid", "high"]):
        edpi = base_edpi[style]
        sens = edpi / dpi_s
        with cols[i]:
            st.markdown(
                f"<div style='font-size:0.8rem; color:#aaaaaa;'>"
                f"{labels[style]}: 感度 {sens:.4f}<br/>eDPI {edpi:.0f}</div>",
                unsafe_allow_html=True,
            )


def render_result_screen():
    st.markdown("## ③ 診断結果 📊")

    dpi_s = st.session_state.dpi
    base_edpi = st.session_state.base_edpi
    final_sens = st.session_state.base_sens
    final_edpi = final_sens * dpi_s

    _, judged_label = classify_style(final_edpi, base_edpi)

    st.success("A/Bテストが終了しました。おつかれさまです！")

    # --- 最終感度 ---
    st.markdown("### 最終結果")
    st.write(f"- ゲーム：{st.session_state.game_name}")
    st.write(f"- DPI：{dpi_s}")
    st.write(f"- 最終おすすめ eDPI：**{final_edpi:.1f}**")
    st.write(f"- 最終おすすめ 感度：**DPI {dpi_s} / 感度 {final_sens:.4f}**")
    st.write(f"- （参考）このeDPIは「{judged_label}」に近い位置です。")

    # --- 環境情報（あれば表示） ---
    env_info = st.session_state.env_info
    if env_info:
        st.markdown("### 環境情報（参考）🌡")
        # どれか1つでも入力されていれば表示
        has_any = any(v for v in env_info.values())
        if has_any:
            if env_info.get("temp"):
                st.write(f"- 室温：{env_info['temp']}")
            if env_info.get("humid"):
                st.write(f"- 湿度：{env_info['humid']}")
            if env_info.get("weather"):
                st.write(f"- 天気：{env_info['weather']}")
            if env_info.get("timeband"):
                st.write(f"- プレイ時間帯：{env_info['timeband']}")
            if env_info.get("note"):
                st.write(f"- メモ：{env_info['note']}")
        else:
            st.caption("※今回、環境情報は入力されていません。")

    # --- 調整履歴（小さめ） ---
    st.markdown(
        "<h4 style='font-size:1.0rem; margin-top:2rem;'>調整履歴（参考）</h4>",
        unsafe_allow_html=True,
    )
    for i, h in enumerate(st.session_state.history, start=1):
        line = (
            f"ラウンド {i}: "
            f"基準感度={h['base_sens']:.4f}, "
            f"ロー候補={h['low_sens']:.4f}, "
            f"ハイ候補={h['high_sens']:.4f}, "
            f"選択={choice_label_jp(h['choice'])}"
        )
        st.markdown(
            f"<p style='font-size:0.85rem; color:#aaaaaa;'>- {line}</p>",
            unsafe_allow_html=True,
        )

    # --- ファイル保存（1回だけ） ---
    if not st.session_state.get("logged_to_file", False):
        log_result_to_file(
            dpi_s,
            st.session_state.game_name,
            base_edpi,
            st.session_state.current_style,
            st.session_state.target_style,
            final_edpi,
            final_sens,
            judged_label,
            st.session_state.history,
            st.session_state.env_info,
            st.session_state.mode_label,
        )
        st.session_state.logged_to_file = True

    st.markdown("---")
    if st.button("最初の設定画面に戻る ⏮"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        init_state()
        st.session_state.page = "setup"
        st.rerun()



# =============================
#  メイン
# =============================

def main():
    init_state()
    set_dark_style()

    page = st.session_state.page
    if page == "setup":
        render_setup_screen()
    elif page == "test":
        render_test_screen()
    else:
        render_result_screen()


if __name__ == "__main__":
    main()
