const I18N = {
  en: {
    weekdays: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
    periodStarted: "Period started",
    periodEnded: "Period ended",
  },
  "zh-Hans": {
    weekdays: ["一", "二", "三", "四", "五", "六", "日"],
    periodStarted: "大姨妈来了",
    periodEnded: "大姨妈走了",
  },
  ja: {
    weekdays: ["月", "火", "水", "木", "金", "土", "日"],
    periodStarted: "生理が来た",
    periodEnded: "生理が終わった",
  },
  ko: {
    weekdays: ["월", "화", "수", "목", "금", "토", "일"],
    periodStarted: "월경 시작",
    periodEnded: "월경 종료",
  },
  fr: {
    weekdays: ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"],
    periodStarted: "Règles commencées",
    periodEnded: "Règles terminées",
  },
  ru: {
    weekdays: ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"],
    periodStarted: "Начало менструации",
    periodEnded: "Окончание менструации",
  },
  es: {
    weekdays: ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"],
    periodStarted: "Comienzo del periodo",
    periodEnded: "Fin del periodo",
  },
};

function normalizeLang(lang) {
  if (!lang || typeof lang !== "string") return "en";
  const l = lang.replace("_", "-");
  if (l.toLowerCase().startsWith("zh")) return "zh-Hans";
  if (l.toLowerCase().startsWith("ja")) return "ja";
  if (l.toLowerCase().startsWith("ko")) return "ko";
  if (l.toLowerCase().startsWith("fr")) return "fr";
  if (l.toLowerCase().startsWith("ru")) return "ru";
  if (l.toLowerCase().startsWith("es")) return "es";
  return "en";
}

function stringsForHass(hass) {
  const lang = normalizeLang(hass?.locale?.language || hass?.language);
  return I18N[lang] || I18N.en;
}

function isoDate(d) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function parseIsoDate(s) {
  if (!s || typeof s !== "string") return null;
  const m = s.match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (!m) return null;
  const d = new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
  if (Number.isNaN(d.getTime())) return null;
  return d;
}

function startOfMonth(d) {
  return new Date(d.getFullYear(), d.getMonth(), 1);
}

function addMonths(d, delta) {
  return new Date(d.getFullYear(), d.getMonth() + delta, 1);
}

function monthLabel(d) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  return `${y}-${m}`;
}

function startOfGrid(monthStart) {
  const dow = monthStart.getDay() || 7;
  return new Date(
    monthStart.getFullYear(),
    monthStart.getMonth(),
    monthStart.getDate() - (dow - 1),
  );
}

function inRange(dayIso, startIso, endIso) {
  if (!dayIso || !startIso || !endIso) return false;
  return startIso <= dayIso && dayIso <= endIso;
}

function todayIso() {
  return isoDate(new Date());
}

function computeAction(strings, records, selectedIso) {
  const today = todayIso();
  if (!selectedIso || selectedIso > today) return { visible: false };

  const byStart = records.find((r) => r && r.start === selectedIso);
  if (byStart) {
    return {
      visible: true,
      kind: "start",
      label: strings.periodStarted,
      checked: true,
      disabled: false,
    };
  }

  const byEnd = records.find((r) => r && r.end === selectedIso);
  if (byEnd) {
    return {
      visible: true,
      kind: "end",
      label: strings.periodEnded,
      checked: true,
      disabled: true,
    };
  }

  const starts = records
    .filter((r) => r && typeof r.start === "string" && r.start <= selectedIso)
    .sort((a, b) => (a.start < b.start ? 1 : -1));
  const last = starts.length ? starts[0] : null;

  if (last) {
    const ds = parseIsoDate(last.start);
    const de = parseIsoDate(selectedIso);
    if (ds && de) {
      const diff = Math.floor(
        (de.getTime() - ds.getTime()) / (24 * 3600 * 1000),
      );
      if (diff <= 7) {
        return {
          visible: true,
          kind: "end",
          label: strings.periodEnded,
          checked: false,
          disabled: false,
        };
      }
    }
  }

  return {
    visible: true,
    kind: "start",
    label: strings.periodStarted,
    checked: false,
    disabled: false,
  };
}

class MenstruationMonthPanel extends HTMLElement {
  setConfig(config) {
    if (!config) throw new Error("Invalid config");
    this._config = {
      data_entity: config.data_entity || "sensor.menstruation_calendar_data",
    };
    this._root = this.attachShadow({ mode: "open" });
    this._month = null;
    this._selectedIso = isoDate(new Date());
    this._loading = false;
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  getCardSize() {
    return 10;
  }

  _getData() {
    const ent = this._hass?.states?.[this._config.data_entity];
    return ent?.attributes || {};
  }

  _ensureMonth() {
    const selected = parseIsoDate(this._selectedIso);
    if (
      this._month &&
      selected &&
      this._month.getFullYear() === selected.getFullYear() &&
      this._month.getMonth() === selected.getMonth()
    ) {
      return;
    }
    if (this._month) return;
    this._month = startOfMonth(selected || new Date());
  }

  _setMonth(delta) {
    this._ensureMonth();
    this._month = addMonths(this._month, delta);
    this._render();
  }

  _jumpToToday() {
    const today = new Date();
    this._selectedIso = isoDate(today);
    this._month = startOfMonth(today);
    this._render();
  }

  _selectDay(iso) {
    if (!iso) return;
    this._selectedIso = iso;
    this._render();
  }

  async _apply() {
    if (this._loading) return;
    const data = this._getData();
    const records = Array.isArray(data.records) ? data.records : [];
    const strings = stringsForHass(this._hass);
    const action = computeAction(strings, records, this._selectedIso);
    if (!action.visible || action.disabled) return;

    this._loading = true;
    this._render();
    try {
      await this._hass.callService("menstruation", "apply_day", {
        date: this._selectedIso,
      });
    } finally {
      this._loading = false;
      this._render();
    }
  }

  _render() {
    if (!this._root || !this._config || !this._hass) return;
    this._ensureMonth();

    const data = this._getData();
    const records = Array.isArray(data.records) ? data.records : [];
    const predicted = data.predicted_period || {};
    const fertile = data.fertile_window || {};

    const monthStart = startOfMonth(this._month);
    const gridStart = startOfGrid(monthStart);

    const weeks = [];
    let cursor = new Date(gridStart);
    for (let w = 0; w < 6; w += 1) {
      const row = [];
      for (let i = 0; i < 7; i += 1) {
        row.push(new Date(cursor));
        cursor.setDate(cursor.getDate() + 1);
      }
      weeks.push(row);
    }

    const strings = stringsForHass(this._hass);
    const action = computeAction(strings, records, this._selectedIso);

    const style = `
      :host { display:block !important; width: 100% !important; max-width: 100% !important; margin: 0 auto !important; }
      *, *::before, *::after { box-sizing: border-box; }
      .panel { width: 100% !important; max-width: 100% !important; margin: 0 auto !important; border-radius: 16px; overflow:hidden; background: var(--ha-card-background, var(--card-background-color, #111)); }
      .head { display:flex; align-items:center; justify-content:space-between; padding: 10px 12px; }
      .title { font-weight: 900; letter-spacing: .5px; font-size: 20px; }
      .btn { cursor:pointer; user-select:none; padding: 6px 10px; border-radius: 10px; background: rgba(255,255,255,.06); }
      .grid { width: 100%; max-width: 100%; padding: 0 10px 12px; }
      .weekdays { width: 100%; display:grid; grid-template-columns:repeat(7, minmax(0, 1fr)); gap: 6px; padding: 6px 0 10px; opacity:.9; font-size: 15px; font-weight: 800; text-align:center; }
      .weeks { display:grid; grid-template-rows:repeat(6,1fr); gap: 6px; }
      .week { width: 100%; display:grid; grid-template-columns:repeat(7, minmax(0, 1fr)); gap: 6px; }
      .cell { min-width: 0; position:relative; height: 50px; border-radius: 14px; display:flex; align-items:center; justify-content:center; cursor:pointer; font-size: 20px; font-weight: 900; }
      .cell:hover { background: rgba(255,255,255,.06); }
      .cell.muted { opacity: .45; }
      .cell.selected { outline: 2px solid rgba(255, 119, 169, .95); background: rgba(255, 119, 169, .14); }
      .cell::before { content:""; position:absolute; width: 34px; height: 34px; border-radius: 50%; opacity: 0; background: transparent; }
      .cell.period::before { opacity: .30; background: #ff4d8d; }
      .cell.predicted::before { opacity: .20; background: #ff77a9; }
      .cell.fertile::before { opacity: .20; background: #ffd166; }
      .cell span { position:relative; z-index:1; }
      .cell.today::after { content:""; position:absolute; left: 50%; bottom: 6px; transform: translateX(-50%); width: 6px; height: 6px; border-radius: 50%; background: rgba(0, 200, 83, .95); }
      .op { border-top: 1px solid rgba(255,255,255,.08); padding: 14px 14px; cursor: pointer; }
      .op.hidden { display:none; }
      .row { display:flex; align-items:center; justify-content:space-between; gap: 12px; }
      .label { font-weight: 900; font-size: 16px; color: var(--primary-text-color, #fff); }
      .sub { margin-top: 4px; opacity: .75; font-size: 13px; }
      .switch { position: relative; width: 52px; height: 32px; pointer-events: none; }
      .switch input { opacity:0; width:0; height:0; }
      .slider { position:absolute; cursor:pointer; inset:0; background: rgba(255,255,255,.18); transition: .2s; border-radius: 999px; }
      .slider:before { content:""; position:absolute; height: 26px; width: 26px; left: 3px; top: 3px; background: #fff; transition: .2s; border-radius: 50%; box-shadow: 0 2px 6px rgba(0,0,0,.35); }
      input:checked + .slider { background: rgba(255, 77, 141, .85); }
      input:checked + .slider:before { transform: translateX(20px); }
      .disabled { opacity:.45; pointer-events:none; }
      .loading { opacity:.65; pointer-events:none; }
    `;

    const opTitle = action.visible ? `${this._selectedIso}` : "";
    const opLabel = action.visible ? action.label : "";
    const checked = action.visible && action.checked;
    const disabled = action.visible && action.disabled;

    const html = `
      <style>${style}</style>
      <div class="panel">
        <div class="head">
          <div class="btn" id="prev">‹</div>
          <div class="title" id="month">${monthLabel(monthStart)}</div>
          <div class="btn" id="next">›</div>
        </div>
        <div class="grid">
          <div class="weekdays">${strings.weekdays.map((d) => `<div>${d}</div>`).join("")}</div>
          <div class="weeks">
            ${weeks
              .map((row) => {
                return `<div class="week">${row
                  .map((d) => {
                    const iso = isoDate(d);
                    const isMuted = d.getMonth() !== monthStart.getMonth();
                    const isSelected = this._selectedIso === iso;
                    const isToday = iso === todayIso();

                    let hasPeriod = false;
                    for (const r of records) {
                      const s = r?.start;
                      let e = r?.end;
                      if (!e && typeof s === "string") {
                        const ds = parseIsoDate(s);
                        if (ds) {
                          ds.setDate(ds.getDate() + 2);
                          e = isoDate(ds);
                        }
                      }
                      if (!e) e = r?.start;
                      if (typeof s === "string" && typeof e === "string" && inRange(iso, s, e)) {
                        hasPeriod = true;
                        break;
                      }
                    }

                    const inPredicted =
                      typeof predicted.start === "string" &&
                      typeof predicted.end === "string" &&
                      inRange(iso, predicted.start, predicted.end);
                    const inFertile =
                      typeof fertile.start === "string" &&
                      typeof fertile.end === "string" &&
                      inRange(iso, fertile.start, fertile.end);

                    const typeClass = hasPeriod ? "period" : (inPredicted ? "predicted" : (inFertile ? "fertile" : ""));
                    const cls = ["cell", typeClass, isMuted ? "muted" : "", isSelected ? "selected" : "", isToday ? "today" : ""]
                      .filter(Boolean)
                      .join(" ");
                    return `<div class="${cls}" data-iso="${iso}"><span>${d.getDate()}</span></div>`;
                  })
                  .join("")}</div>`;
              })
              .join("")}
          </div>
        </div>
        <div class="op ${action.visible ? "" : "hidden"} ${disabled ? "disabled" : ""} ${this._loading ? "loading" : ""}">
          <div class="row">
            <div>
              <div class="label">${opLabel}</div>
              <div class="sub">${opTitle}</div>
            </div>
            <label class="switch">
              <input id="toggle" type="checkbox" ${checked ? "checked" : ""} ${disabled ? "disabled" : ""} />
              <span class="slider"></span>
            </label>
          </div>
        </div>
      </div>
    `;

    this._root.innerHTML = html;
    this._root.getElementById("prev").onclick = () => this._setMonth(-1);
    this._root.getElementById("next").onclick = () => this._setMonth(1);
    const monthEl = this._root.getElementById("month");
    if (monthEl) monthEl.onclick = () => this._jumpToToday();
    this._root.querySelectorAll(".cell").forEach((el) => {
      el.onclick = () => this._selectDay(el.getAttribute("data-iso"));
    });
    const op = this._root.querySelector(".op");
    if (op && action.visible && !disabled) {
      op.onclick = (e) => {
        e.preventDefault();
        e.stopPropagation();
        this._apply();
      };
    }
  }
}

customElements.define("menstruation-month-panel", MenstruationMonthPanel);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "menstruation-month-panel",
  name: "Menstruation Month Panel",
  description: "Month view + period action switch",
});
