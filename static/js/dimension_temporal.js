// ClimaTec - Etapa 4 / Dimension Temporal.
// Dibuja los indicadores y las tres visualizaciones (SVG) con el JSON que imprime la
// plantilla (#tem-datos), calculado en scripts/temporal.py sobre las series mensuales
// reales de clima_limpio.csv. Sin librerias externas ni imagenes.
// Filtro 1: Anio. Filtro 2: Serie / indicador.

(function () {
    'use strict';

    var nodo = document.getElementById('tem-datos');
    if (!nodo) return;
    var D = JSON.parse(nodo.textContent);

    var NS = 'http://www.w3.org/2000/svg';
    var COLOR = { co2: '#ffb454', gis: '#ff6a4d', gcag: '#49c7e0' };
    var MESES = D.meses;

    // ---- Utilidades ---------------------------------------------------------
    function el(id) { return document.getElementById(id); }
    function vaciar(n) { while (n.firstChild) n.removeChild(n.firstChild); }
    function crear(tag, clase, texto) {
        var n = document.createElement(tag);
        if (clase) n.className = clase;
        if (texto !== undefined) n.textContent = texto;
        return n;
    }
    function svg(tag, attrs) {
        var n = document.createElementNS(NS, tag);
        Object.keys(attrs || {}).forEach(function (k) { n.setAttribute(k, attrs[k]); });
        return n;
    }
    function texto(x, y, t, attrs) {
        var n = svg('text', Object.assign({ x: x, y: y, fill: 'rgba(244,247,251,.6)', 'font-size': 10 }, attrs || {}));
        n.textContent = t;
        return n;
    }
    function dec(n, d) { return n.toLocaleString('es-CO', { minimumFractionDigits: d, maximumFractionDigits: d }); }
    function signo(n, d) { return (n > 0 ? '+' : '') + dec(Math.abs(n) < 0.5 * Math.pow(10, -d) ? 0 : n, d); }
    function media(a) { var s = 0; a.forEach(function (v) { s += v; }); return a.length ? s / a.length : null; }

    // ---- Tooltip ------------------------------------------------------------
    var tip = crear('div', 'pob-tip');
    tip.setAttribute('role', 'tooltip');
    tip.hidden = true;
    document.body.appendChild(tip);
    function mostrarTip(ev, t) {
        tip.textContent = t; tip.hidden = false;
        var x = ev.clientX + 14, y = ev.clientY + 14, w = tip.offsetWidth, h = tip.offsetHeight;
        if (x + w > window.innerWidth - 8) x = ev.clientX - w - 14;
        if (y + h > window.innerHeight - 8) y = ev.clientY - h - 14;
        tip.style.left = x + 'px'; tip.style.top = y + 'px';
    }
    function ocultarTip() { tip.hidden = true; }
    function conTip(n, t) {
        n.addEventListener('mousemove', function (ev) { mostrarTip(ev, t); });
        n.addEventListener('mouseleave', ocultarTip);
        n.addEventListener('focus', function () {
            var r = n.getBoundingClientRect();
            mostrarTip({ clientX: r.left + r.width / 2, clientY: r.top }, t);
        });
        n.addEventListener('blur', ocultarTip);
    }

    // ---- Datos ya organizados ----------------------------------------------
    var SERIES = {};
    D.series.forEach(function (s) { SERIES[s.clave] = s; });
    function anuales(clave) {
        var por = {};
        SERIES[clave].puntos.forEach(function (p) { (por[p[0]] = por[p[0]] || []).push(p); });
        return Object.keys(por).map(Number).sort().map(function (y) {
            var v = por[y].map(function (p) { return p[2]; });
            return { anio: y, media: media(v), n: v.length, completo: v.length === 12, puntos: por[y] };
        });
    }
    var ANUAL = {};
    Object.keys(SERIES).forEach(function (k) { ANUAL[k] = anuales(k); });

    function desviacionesPorMes(clave, soloAnio) {
        var acc = []; for (var m = 0; m < 12; m++) acc.push([]);
        ANUAL[clave].forEach(function (a) {
            if (!a.completo) return;
            if (soloAnio && a.anio !== soloAnio) return;
            a.puntos.forEach(function (p) { acc[p[1] - 1].push(p[2] - a.media); });
        });
        return acc.map(function (v) { return v.length ? media(v) : null; });
    }

    // ---- Estado y filtros ---------------------------------------------------
    var estado = { anio: 'todos', ind: 'co2' };
    var selAnio = el('tem-f-anio'), selInd = el('tem-f-ind');
    var o0 = crear('option', '', 'Todos los anios (' + D.anios[0] + '-' + D.anios[D.anios.length - 1] + ')');
    o0.value = 'todos'; selAnio.appendChild(o0);
    D.anios.forEach(function (a) { var o = crear('option', '', String(a)); o.value = String(a); selAnio.appendChild(o); });
    D.series.forEach(function (s) { var o = crear('option', '', s.nombre + ' (' + s.unidad + ')'); o.value = s.clave; selInd.appendChild(o); });

    function d2(clave) { return 2; }
    function unidad(clave) { return SERIES[clave].unidad; }

    // ---- Indicadores --------------------------------------------------------
    function cambioAnual(clave) {
        var an = ANUAL[clave];
        if (estado.anio === 'todos') {
            var difs = [];
            for (var i = 1; i < an.length; i++) {
                if (an[i].completo && an[i - 1].completo) difs.push(an[i].media - an[i - 1].media);
            }
            return difs.length ? { v: media(difs), txt: 'promedio de ' + difs.length + ' aumentos anuales entre anios completos' } : null;
        }
        var y = parseInt(estado.anio, 10);
        var a = an.filter(function (x) { return x.anio === y; })[0];
        var p = an.filter(function (x) { return x.anio === y - 1; })[0];
        if (!a || !p) return null;
        var meses = a.puntos.map(function (q) { return q[1]; });
        var prev = p.puntos.filter(function (q) { return meses.indexOf(q[1]) >= 0; }).map(function (q) { return q[2]; });
        var act = a.puntos.map(function (q) { return q[2]; });
        if (!prev.length) return null;
        return { v: media(act) - media(prev), txt: y + ' frente a ' + (y - 1) + (a.completo ? '' : ' (mismos ' + meses.length + ' meses)') };
    }
    function puntosFiltro(clave) {
        return SERIES[clave].puntos.filter(function (p) { return estado.anio === 'todos' || String(p[0]) === estado.anio; });
    }
    function renderIndicadores() {
        var s = SERIES[estado.ind], pts = puntosFiltro(estado.ind);
        if (estado.anio === 'todos') {
            el('tem-i1-valor').textContent = String(pts.length);
            el('tem-i1-sub').textContent = s.nombre + ' · ' + s.fuente;
        } else {
            el('tem-i1-valor').textContent = pts.length + ' / 12';
            el('tem-i1-sub').textContent = s.nombre + ' · ' + estado.anio + (pts.length < 12 ? ' (anio parcial)' : '');
        }
        var c = cambioAnual(estado.ind);
        if (c) {
            el('tem-i2-valor').textContent = signo(c.v, 2) + ' ' + s.unidad;
            el('tem-i2-etq').textContent = estado.anio === 'todos' ? 'aumento anual medio del promedio' : 'cambio del promedio frente al anio anterior';
            el('tem-i2-sub').textContent = c.txt;
        } else {
            el('tem-i2-valor').textContent = '-';
            el('tem-i2-etq').textContent = 'cambio del promedio anual';
            el('tem-i2-sub').textContent = 'No hay anio anterior con datos para comparar.';
        }
        if (pts.length) {
            var mx = pts.reduce(function (a, b) { return b[2] > a[2] ? b : a; });
            el('tem-i3-valor').textContent = dec(mx[2], 2) + ' ' + s.unidad;
            el('tem-i3-sub').textContent = MESES[mx[1] - 1] + ' ' + mx[0] + ' · ' + s.nombre;
        } else {
            el('tem-i3-valor').textContent = '-'; el('tem-i3-sub').textContent = '';
        }
        var nota = el('tem-nota');
        nota.textContent = (estado.anio !== 'todos' && pts.length === 0)
            ? 'La serie seleccionada no tiene datos en ' + estado.anio + '.' : '';
    }

    // ---- Eje X de tiempo comun ---------------------------------------------
    function ejeY(vals, forzarCero) {
        var mn = Math.min.apply(null, vals), mx = Math.max.apply(null, vals);
        if (forzarCero) { mn = Math.min(mn, 0); mx = Math.max(mx, 0); }
        var pad = (mx - mn) * 0.12 || 1;
        return [mn - (forzarCero && mn === 0 ? 0 : pad), mx + pad];
    }
    function ticksLineales(lo, hi, n) {
        var paso = (hi - lo) / n, mag = Math.pow(10, Math.floor(Math.log10(paso)));
        var f = paso / mag; paso = (f < 1.5 ? 1 : f < 3.5 ? 2 : f < 7.5 ? 5 : 10) * mag;
        var t = [], v = Math.ceil(lo / paso) * paso;
        for (; v <= hi + 1e-9; v += paso) t.push(Math.round(v / paso) * paso);
        return t;
    }
    function fmtTick(v) { return Math.abs(v) >= 100 ? dec(v, 0) : dec(v, Math.abs(v) < 10 ? 1 : 0); }

    // ---- Visualizacion 1: serie mensual + tendencia + eventos --------------
    function renderV1() {
        var s = SERIES[estado.ind], cont = el('tem-v1'), color = COLOR[estado.ind];
        vaciar(cont);
        el('tem-v1-titulo').textContent = 'Evolucion mensual de ' + s.nombre;
        el('tem-v1-sub').textContent = s.puntos.length + ' meses · ' + s.fuente + (estado.anio === 'todos' ? '' : ' · anio ' + estado.anio + ' resaltado');
        el('tem-v1-sw').style.background = color;

        var W = 640, H = 340, mL = 58, mR = 16, mT = 22, mB = 44, pw = W - mL - mR, ph = H - mT - mB;
        var t0 = D.anios[0], t1 = D.anios[D.anios.length - 1] + 1;
        var xs = s.puntos.map(function (p) { return p[0] + (p[1] - 0.5) / 12; });
        var ys = s.puntos.map(function (p) { return p[2]; });
        var rng = ejeY(ys, false), lo = rng[0], hi = rng[1];
        function X(t) { return mL + (t - t0) / (t1 - t0) * pw; }
        function Y(v) { return mT + ph - (v - lo) / (hi - lo) * ph; }

        var g = svg('svg', { viewBox: '0 0 ' + W + ' ' + H, width: '100%', 'aria-hidden': 'true', 'class': 'pob-svg' });
        ticksLineales(lo, hi, 5).forEach(function (v) {
            g.appendChild(svg('line', { x1: mL, x2: mL + pw, y1: Y(v), y2: Y(v), stroke: 'rgba(255,255,255,.07)' }));
            g.appendChild(texto(mL - 8, Y(v) + 3, fmtTick(v), { 'text-anchor': 'end' }));
        });
        for (var y = t0; y <= t1; y++) {
            g.appendChild(svg('line', { x1: X(y), x2: X(y), y1: mT, y2: mT + ph, stroke: 'rgba(255,255,255,.05)' }));
            if (y < t1) g.appendChild(texto(X(y + 0.5), mT + ph + 16, String(y), { 'text-anchor': 'middle', fill: String(y) === estado.anio ? '#fff' : 'rgba(244,247,251,.6)', 'font-weight': String(y) === estado.anio ? 700 : 400 }));
        }
        var yt = texto(14, mT + ph / 2, s.nombre + ' (' + s.unidad_txt + ')', { 'text-anchor': 'middle', fill: 'rgba(244,247,251,.72)', 'font-size': 11 });
        yt.setAttribute('transform', 'rotate(-90 14 ' + (mT + ph / 2) + ')');
        g.appendChild(yt);

        if (estado.anio !== 'todos') {
            var ya = parseInt(estado.anio, 10);
            g.appendChild(svg('rect', { x: X(ya), y: mT, width: X(ya + 1) - X(ya), height: ph, fill: 'rgba(255,255,255,.06)' }));
        }

        var tr = D.tendencias[estado.ind];
        g.appendChild(svg('line', { x1: X(t0), y1: Y(tr.intercepto + tr.pendiente * t0), x2: X(t1), y2: Y(tr.intercepto + tr.pendiente * t1), stroke: '#ffb454', 'stroke-dasharray': '6 4', 'stroke-width': 1.5, opacity: .9 }));

        var enFiltro = function (p) { return estado.anio === 'todos' || String(p[0]) === estado.anio; };
        g.appendChild(svg('polyline', {
            points: xs.map(function (x, i) { return X(x) + ',' + Y(ys[i]); }).join(' '),
            fill: 'none', stroke: color, 'stroke-width': 2, 'stroke-linejoin': 'round', opacity: estado.anio === 'todos' ? 1 : .35
        }));
        s.puntos.forEach(function (p, i) {
            var on = enFiltro(p);
            var c = svg('circle', { cx: X(xs[i]), cy: Y(ys[i]), r: on ? 3.4 : 2, fill: color, opacity: on ? 1 : .4, stroke: 'rgba(0,0,0,.35)', 'stroke-width': .5, tabindex: '0', 'class': 'rel-punto' });
            conTip(c, MESES[p[1] - 1] + ' ' + p[0] + ': ' + dec(p[2], 2) + ' ' + s.unidad);
            g.appendChild(c);
        });

        D.eventos.forEach(function (e) {
            var x = X(e.anio + (e.mes - 0.5) / 12);
            if (x < mL || x > mL + pw) return;
            g.appendChild(svg('line', { x1: x, x2: x, y1: mT + 8, y2: mT + ph, stroke: 'rgba(255,180,84,.45)', 'stroke-dasharray': '2 3' }));
            var r = svg('path', { d: 'M' + x + ' ' + (mT + 1) + ' L' + (x + 6) + ' ' + (mT + 8) + ' L' + x + ' ' + (mT + 15) + ' L' + (x - 6) + ' ' + (mT + 8) + ' Z', fill: '#ffb454', stroke: 'rgba(0,0,0,.4)', tabindex: '0', 'class': 'rel-evento' });
            conTip(r, e.fecha + ' · ' + e.evento);
            g.appendChild(r);
        });
        cont.appendChild(g);

        var pts = puntosFiltro(estado.ind);
        if (pts.length >= 2) {
            var primero = pts[0], ultimo = pts[pts.length - 1];
            el('tem-v1-lectura').textContent = 'Lectura del filtro actual: de ' + MESES[primero[1] - 1] + ' ' + primero[0] + ' (' + dec(primero[2], 2) + ' ' + s.unidad +
                ') a ' + MESES[ultimo[1] - 1] + ' ' + ultimo[0] + ' (' + dec(ultimo[2], 2) + ' ' + s.unidad + '); la tendencia de toda la serie es ' +
                signo(tr.pendiente, 3) + ' ' + s.unidad + ' por anio (R² = ' + dec(tr.r2, 2) + ').';
        } else { el('tem-v1-lectura').textContent = ''; }
    }

    // ---- Visualizacion 2: perfil estacional ---------------------------------
    function renderV2() {
        var s = SERIES[estado.ind], cont = el('tem-v2'), color = COLOR[estado.ind];
        vaciar(cont);
        var anioSel = estado.anio === 'todos' ? null : parseInt(estado.anio, 10);
        var an = ANUAL[estado.ind].filter(function (a) { return a.anio === anioSel; })[0];
        var usaAnio = anioSel !== null && an && an.completo;
        var dev = desviacionesPorMes(estado.ind, usaAnio ? anioSel : null);
        el('tem-v2-titulo').textContent = 'Perfil estacional de ' + s.nombre;
        el('tem-v2-sub').textContent = 'Desviacion de cada mes respecto al promedio de su anio · ' +
            (usaAnio ? 'anio ' + anioSel : 'promedio de los anios completos');
        el('tem-nota').textContent = (anioSel !== null && !usaAnio && an) ? estadoNota(an) : el('tem-nota').textContent;

        var W = 640, H = 320, mL = 58, mR = 16, mT = 24, mB = 40, pw = W - mL - mR, ph = H - mT - mB;
        var vals = dev.filter(function (v) { return v !== null; });
        if (!vals.length) { cont.appendChild(crear('p', 'pob-mini', 'No hay anios completos para calcular el perfil estacional.')); el('tem-v2-lectura').textContent = ''; return; }
        var rng = ejeY(vals, true), lo = rng[0], hi = rng[1];
        function Y(v) { return mT + ph - (v - lo) / (hi - lo) * ph; }
        var banda = pw / 12, bw = banda * 0.6;
        var imax = dev.indexOf(Math.max.apply(null, vals)), imin = dev.indexOf(Math.min.apply(null, vals));

        var g = svg('svg', { viewBox: '0 0 ' + W + ' ' + H, width: '100%', 'aria-hidden': 'true', 'class': 'pob-svg' });
        ticksLineales(lo, hi, 5).forEach(function (v) {
            g.appendChild(svg('line', { x1: mL, x2: mL + pw, y1: Y(v), y2: Y(v), stroke: Math.abs(v) < 1e-9 ? 'rgba(255,255,255,.35)' : 'rgba(255,255,255,.06)' }));
            g.appendChild(texto(mL - 8, Y(v) + 3, fmtTick(v), { 'text-anchor': 'end' }));
        });
        var yt = texto(14, mT + ph / 2, 'Desviacion (' + s.unidad + ')', { 'text-anchor': 'middle', fill: 'rgba(244,247,251,.72)', 'font-size': 11 });
        yt.setAttribute('transform', 'rotate(-90 14 ' + (mT + ph / 2) + ')');
        g.appendChild(yt);
        dev.forEach(function (v, i) {
            var cx = mL + banda * i + banda / 2;
            g.appendChild(texto(cx, mT + ph + 18, MESES[i], { 'text-anchor': 'middle', fill: 'rgba(244,247,251,.72)', 'font-size': 11 }));
            if (v === null) return;
            var y0 = Y(0), y1 = Y(v);
            var fill = i === imax ? '#ff6a4d' : (i === imin ? '#49c7e0' : color);
            var r = svg('rect', { x: cx - bw / 2, y: Math.min(y0, y1), width: bw, height: Math.max(Math.abs(y1 - y0), 1.5), rx: 3, fill: fill, 'fill-opacity': (i === imax || i === imin) ? 1 : .7, tabindex: '0', 'class': 'pob-col' });
            conTip(r, MESES[i] + ': ' + signo(v, 2) + ' ' + s.unidad + ' frente al promedio del anio');
            g.appendChild(r);
            g.appendChild(texto(cx, v >= 0 ? y1 - 5 : y1 + 13, signo(v, 2), { 'text-anchor': 'middle', fill: '#f4f7fb', 'font-weight': 600, 'font-size': 9.5 }));
        });
        cont.appendChild(g);

        var amp = dev[imax] - dev[imin];
        el('tem-v2-lectura').textContent = 'Lectura del filtro actual: el mes mas alto respecto a su anio es ' + MESES[imax] + ' (' + signo(dev[imax], 2) +
            ' ' + s.unidad + ') y el mas bajo ' + MESES[imin] + ' (' + signo(dev[imin], 2) + ' ' + s.unidad + '); la diferencia es ' + dec(amp, 2) + ' ' + s.unidad + '.';
    }
    function estadoNota(a) { return 'El anio ' + a.anio + ' tiene ' + a.n + ' meses (parcial): el perfil muestra el promedio de los anios completos.'; }

    // ---- Visualizacion 3: promedio anual y cambio ---------------------------
    function renderV3() {
        var s = SERIES[estado.ind], cont = el('tem-v3'), color = COLOR[estado.ind], an = ANUAL[estado.ind];
        vaciar(cont);
        el('tem-v3-titulo').textContent = 'Promedio anual de ' + s.nombre;
        var cero = estado.ind !== 'co2';
        el('tem-v3-sub').textContent = 'Promedio por anio y cambio frente al anterior' + (cero ? '' : ' · el eje no parte de cero para ver las diferencias');

        var W = 640, H = 340, mL = 58, mR = 16, mT = 26, mB = 56, pw = W - mL - mR, ph = H - mT - mB;
        var vals = an.map(function (a) { return a.media; });
        var rng = ejeY(vals, cero), lo = rng[0], hi = rng[1];
        function Y(v) { return mT + ph - (v - lo) / (hi - lo) * ph; }
        var banda = pw / an.length, bw = Math.min(70, banda * 0.6);

        var g = svg('svg', { viewBox: '0 0 ' + W + ' ' + H, width: '100%', 'aria-hidden': 'true', 'class': 'pob-svg' });
        ticksLineales(lo, hi, 5).forEach(function (v) {
            g.appendChild(svg('line', { x1: mL, x2: mL + pw, y1: Y(v), y2: Y(v), stroke: 'rgba(255,255,255,.07)' }));
            g.appendChild(texto(mL - 8, Y(v) + 3, fmtTick(v), { 'text-anchor': 'end' }));
        });
        var yt = texto(14, mT + ph / 2, s.nombre + ' (' + s.unidad + ')', { 'text-anchor': 'middle', fill: 'rgba(244,247,251,.72)', 'font-size': 11 });
        yt.setAttribute('transform', 'rotate(-90 14 ' + (mT + ph / 2) + ')');
        g.appendChild(yt);

        an.forEach(function (a, i) {
            var cx = mL + banda * i + banda / 2, y = Y(a.media), base = cero ? Y(0) : Y(lo);
            var sel = String(a.anio) === estado.anio;
            var r = svg('rect', {
                x: cx - bw / 2, y: Math.min(y, base), width: bw, height: Math.max(Math.abs(base - y), 1.5), rx: 3,
                fill: sel ? '#ff6a4d' : color, 'fill-opacity': a.completo ? .85 : .35,
                stroke: a.completo ? 'none' : color, 'stroke-dasharray': a.completo ? '' : '4 3', tabindex: '0', 'class': 'pob-col'
            });
            conTip(r, a.anio + ': ' + dec(a.media, 2) + ' ' + s.unidad + ' · ' + a.n + ' meses' + (a.completo ? '' : ' (parcial)'));
            g.appendChild(r);
            g.appendChild(texto(cx, y - 6, dec(a.media, 2), { 'text-anchor': 'middle', fill: '#f4f7fb', 'font-weight': 600, 'font-size': 10.5 }));
            g.appendChild(texto(cx, mT + ph + 16, String(a.anio) + (a.completo ? '' : '*'), { 'text-anchor': 'middle', fill: sel ? '#fff' : 'rgba(244,247,251,.72)', 'font-size': 11, 'font-weight': sel ? 700 : 400 }));
            if (i > 0 && a.completo && an[i - 1].completo) {
                var d = a.media - an[i - 1].media;
                g.appendChild(texto(cx, mT + ph + 32, signo(d, 2), { 'text-anchor': 'middle', fill: d > 0 ? '#ff9d8a' : '#7be2a8', 'font-size': 10.5, 'font-weight': 600 }));
            }
        });
        g.appendChild(texto(mL, H - 6, '* anio parcial (menos de 12 meses). Debajo de cada anio: cambio frente al anterior (' + s.unidad + ').', { fill: 'rgba(244,247,251,.5)', 'font-size': 10 }));
        cont.appendChild(g);

        var comp = an.filter(function (a) { return a.completo; });
        if (comp.length >= 2) {
            var mejor = null;
            for (var i = 1; i < comp.length; i++) {
                if (comp[i].anio - comp[i - 1].anio !== 1) continue;
                var d = comp[i].media - comp[i - 1].media;
                if (!mejor || Math.abs(d) > Math.abs(mejor.d)) mejor = { d: d, a: comp[i - 1].anio, b: comp[i].anio };
            }
            var altoA = comp.reduce(function (a, b) { return b.media > a.media ? b : a; });
            el('tem-v3-lectura').textContent = 'Lectura del filtro actual: entre anios completos, ' + s.nombre + ' va de ' + dec(comp[0].media, 2) + ' a ' +
                dec(comp[comp.length - 1].media, 2) + ' ' + s.unidad + '; el mayor cambio es ' + signo(mejor.d, 2) + ' ' + s.unidad + ' (' + mejor.a + ' a ' + mejor.b +
                ') y el promedio mas alto es el de ' + altoA.anio + '.';
        } else { el('tem-v3-lectura').textContent = ''; }
    }

    // ---- Tabla de apoyo -----------------------------------------------------
    function renderApoyo() {
        var tb = el('tem-a-tabla'); vaciar(tb);
        D.anios.forEach(function (y, i) {
            var c = ANUAL.co2.filter(function (a) { return a.anio === y; })[0];
            var cp = ANUAL.co2.filter(function (a) { return a.anio === y - 1; })[0];
            var gi = ANUAL.gis.filter(function (a) { return a.anio === y; })[0];
            var gc = ANUAL.gcag.filter(function (a) { return a.anio === y; })[0];
            var tr = crear('tr', String(y) === estado.anio ? 'rel-fila-sel' : '');
            var delta = (c && cp && c.completo && cp.completo) ? signo(c.media - cp.media, 2) : '-';
            function celda(a, d) { return a ? dec(a.media, d) + (a.completo ? '' : ' *') : '-'; }
            [[String(y), 'mono'], [c ? String(c.n) : '-', 'mono'], [celda(c, 2), 'mono'], [delta, 'mono'], [celda(gi, 2), 'mono'], [celda(gc, 2), 'mono']]
                .forEach(function (x) { tr.appendChild(crear('td', x[1], x[0])); });
            tb.appendChild(tr);
        });
    }

    function renderTodo() {
        ocultarTip();
        el('tem-nota').textContent = '';
        renderIndicadores(); renderV1(); renderV2(); renderV3(); renderApoyo();
    }

    selAnio.addEventListener('change', function () { estado.anio = selAnio.value; renderTodo(); });
    selInd.addEventListener('change', function () { estado.ind = selInd.value; renderTodo(); });
    el('tem-f-reset').addEventListener('click', function () {
        estado.anio = 'todos'; estado.ind = 'co2'; selAnio.value = 'todos'; selInd.value = 'co2'; renderTodo();
    });

    renderTodo();
})();
