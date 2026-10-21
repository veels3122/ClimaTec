// ClimaTec - Etapa 4 / Dimension Relacional Multidimensional.
// Dibuja los indicadores y las tres visualizaciones (SVG) con el JSON que imprime
// la plantilla (#rel-datos), calculado en scripts/relacional.py sobre clima_limpio.csv
// y eventos_externos_muestra.csv. Sin librerias externas ni imagenes.
// Filtro 1: Anio. Filtro 2: Indicador a relacionar con la poblacion.

(function () {
    'use strict';

    var nodo = document.getElementById('rel-datos');
    if (!nodo) return;
    var D = JSON.parse(nodo.textContent);

    var NS = 'http://www.w3.org/2000/svg';
    var COLORES = ['#49c7e0', '#ff6a4d', '#ffb454', '#3ddc97', '#c9b6ff', '#6a8bff'];
    var COLOR_FOCO = '#ffffff';

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
    function entero(n) { return Math.round(n).toLocaleString('es-CO'); }
    function dec(n, d) { return n.toLocaleString('es-CO', { minimumFractionDigits: d, maximumFractionDigits: d }); }
    function signo(n, d) { return (n > 0 ? '+' : '') + dec(Math.abs(n) < 0.5 * Math.pow(10, -d) ? 0 : n, d) + '%'; }
    function numero(n) {
        if (n >= 100) return entero(n);
        if (n >= 1) return dec(n, 1);
        return n.toLocaleString('es-CO', { maximumFractionDigits: 3 });
    }
    function abrev(n) {
        if (n >= 1e9) return entero(n / 1e9) + ' mil M';
        if (n >= 1e6) return entero(n / 1e6) + ' M';
        if (n >= 1e3) return entero(n / 1e3) + ' mil';
        return entero(n);
    }
    function pob(n) {
        if (n >= 1e9) return dec(n / 1e9, 2) + ' mil millones';
        if (n >= 1e6) return dec(n / 1e6, 1) + ' millones';
        return entero(n);
    }

    // ---- Tooltip ------------------------------------------------------------
    var tip = crear('div', 'pob-tip');
    tip.setAttribute('role', 'tooltip');
    tip.hidden = true;
    document.body.appendChild(tip);
    function mostrarTip(ev, t) {
        tip.textContent = t;
        tip.hidden = false;
        var x = ev.clientX + 14, y = ev.clientY + 14;
        var w = tip.offsetWidth, h = tip.offsetHeight;
        if (x + w > window.innerWidth - 8) x = ev.clientX - w - 14;
        if (y + h > window.innerHeight - 8) y = ev.clientY - h - 14;
        tip.style.left = x + 'px';
        tip.style.top = y + 'px';
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

    // ---- Estado y filtros ---------------------------------------------------
    var estado = { anio: String(D.anio_ref), ind: D.indicadores[0].clave };
    var selAnio = el('rel-f-anio'), selInd = el('rel-f-ind');
    D.anios.forEach(function (a) {
        var o = crear('option', '', String(a)); o.value = String(a); selAnio.appendChild(o);
    });
    selAnio.value = estado.anio;
    D.indicadores.forEach(function (i) {
        var o = crear('option', '', i.nombre + ' (' + i.unidad + ')'); o.value = i.clave; selInd.appendChild(o);
    });

    function infoInd(clave) {
        for (var i = 0; i < D.indicadores.length; i++) if (D.indicadores[i].clave === clave) return D.indicadores[i];
        return D.indicadores[0];
    }
    function mundoAnio(a) {
        for (var i = 0; i < D.mundo.length; i++) if (String(D.mundo[i].anio) === String(a)) return D.mundo[i];
        return null;
    }
    function eventosAnio(a) { return D.eventos.filter(function (e) { return String(e.anio) === String(a); }); }

    // ---- Indicadores --------------------------------------------------------
    function renderIndicadores() {
        var ind = infoInd(estado.ind);
        var d = (D.dispersion[ind.clave] || {})[estado.anio];
        if (d) {
            el('rel-i1-valor').textContent = dec(d.spearman, 2);
            el('rel-i1-sub').textContent = d.n + ' paises · ' + ind.nombre + ' · ' + estado.anio;
            if (d.foco) {
                el('rel-i2-valor').textContent = '#' + d.foco.puesto;
                el('rel-i2-etq').textContent = 'puesto de ' + D.pais_foco + ' entre ' + d.foco.de + ' paises (' + ind.nombre + ')';
                el('rel-i2-sub').textContent = dec(d.foco.razon, 2) + ' veces lo esperado por su poblacion';
            } else {
                el('rel-i2-valor').textContent = '-';
                el('rel-i2-sub').textContent = D.pais_foco + ' no tiene dato para este filtro.';
            }
        } else {
            el('rel-i1-valor').textContent = '-';
            el('rel-i1-sub').textContent = 'Sin datos suficientes para este filtro.';
            el('rel-i2-valor').textContent = '-';
            el('rel-i2-sub').textContent = '';
        }
        var evs = eventosAnio(estado.anio), m = mundoAnio(estado.anio);
        el('rel-i3-valor').textContent = String(evs.length);
        el('rel-i3-etq').textContent = 'eventos externos en ' + estado.anio;
        el('rel-i3-sub').textContent = (m && m.variacion !== null ? 'CO2 mundial ' + signo(m.variacion, 2) + ' · ' : '') +
            (evs.length ? evs.map(function (e) { return e.evento.split(' - ')[0]; }).join('; ') : 'ningun evento registrado');
    }

    // ---- Visualizacion 1: dispersion poblacion x indicador (log-log) --------
    function renderV1() {
        var ind = infoInd(estado.ind);
        var d = (D.dispersion[ind.clave] || {})[estado.anio];
        var cont = el('rel-v1'), ley = el('rel-v1-ley');
        vaciar(cont); vaciar(ley);
        el('rel-v1-titulo').textContent = 'Poblacion frente a ' + ind.nombre + ', por pais';
        if (!d) {
            cont.appendChild(crear('p', 'pob-mini', 'No hay datos suficientes para este indicador y anio.'));
            el('rel-v1-sub').textContent = ''; el('rel-v1-lectura').textContent = '';
            return;
        }
        el('rel-v1-sub').textContent = d.n + ' paises · ' + estado.anio + ' · escala logaritmica en ambos ejes';

        D.grupos.forEach(function (g, i) {
            var s = crear('span'); var sw = crear('i', 'pob-sw'); sw.style.background = COLORES[i];
            s.appendChild(sw); s.appendChild(document.createTextNode(' ' + g)); ley.appendChild(s);
        });
        var sr = crear('span'); sr.appendChild(crear('i', 'rel-recta')); sr.appendChild(document.createTextNode(' Recta de referencia'));
        ley.appendChild(sr);

        var W = 640, H = 380, mL = 58, mR = 16, mT = 16, mB = 52;
        var pw = W - mL - mR, ph = H - mT - mB;
        var xs = d.puntos.map(function (p) { return Math.log10(p[1]); });
        var ys = d.puntos.map(function (p) { return Math.log10(p[2]); });
        var x0 = Math.floor(Math.min.apply(null, xs)), x1 = Math.ceil(Math.max.apply(null, xs));
        var y0 = Math.floor(Math.min.apply(null, ys)), y1 = Math.ceil(Math.max.apply(null, ys));
        if (x1 === x0) x1 += 1; if (y1 === y0) y1 += 1;
        function X(v) { return mL + (v - x0) / (x1 - x0) * pw; }
        function Y(v) { return mT + ph - (v - y0) / (y1 - y0) * ph; }

        var s = svg('svg', { viewBox: '0 0 ' + W + ' ' + H, width: '100%', 'aria-hidden': 'true', 'class': 'pob-svg' });
        var clip = svg('clipPath', { id: 'rel-clip' });
        clip.appendChild(svg('rect', { x: mL, y: mT, width: pw, height: ph }));
        s.appendChild(clip);

        for (var e = x0; e <= x1; e++) {
            s.appendChild(svg('line', { x1: X(e), x2: X(e), y1: mT, y2: mT + ph, stroke: 'rgba(255,255,255,.06)' }));
            s.appendChild(texto(X(e), mT + ph + 16, abrev(Math.pow(10, e)), { 'text-anchor': 'middle' }));
        }
        for (var f = y0; f <= y1; f++) {
            s.appendChild(svg('line', { x1: mL, x2: mL + pw, y1: Y(f), y2: Y(f), stroke: 'rgba(255,255,255,.06)' }));
            s.appendChild(texto(mL - 8, Y(f) + 3, numero(Math.pow(10, f)), { 'text-anchor': 'end' }));
        }
        s.appendChild(svg('rect', { x: mL, y: mT, width: pw, height: ph, fill: 'none', stroke: 'rgba(255,255,255,.12)' }));
        s.appendChild(texto(mL + pw / 2, H - 8, 'Poblacion (habitantes)', { 'text-anchor': 'middle', fill: 'rgba(244,247,251,.72)', 'font-size': 11 }));
        var yt = texto(14, mT + ph / 2, ind.nombre + ' (' + ind.unidad + ')', { 'text-anchor': 'middle', fill: 'rgba(244,247,251,.72)', 'font-size': 11 });
        yt.setAttribute('transform', 'rotate(-90 14 ' + (mT + ph / 2) + ')');
        s.appendChild(yt);

        var recta = svg('line', {
            x1: X(x0), y1: Y(d.intercepto + d.pendiente * x0), x2: X(x1), y2: Y(d.intercepto + d.pendiente * x1),
            stroke: '#ffb454', 'stroke-width': 1.6, 'stroke-dasharray': '6 4', 'clip-path': 'url(#rel-clip)'
        });
        s.appendChild(recta);

        var iFoco = D.nombres.indexOf(D.pais_foco);
        var gPuntos = svg('g', { 'clip-path': 'url(#rel-clip)' });
        var foco = null;
        d.puntos.forEach(function (p) {
            var lx = Math.log10(p[1]), ly = Math.log10(p[2]);
            var razon = Math.pow(10, ly - (d.intercepto + d.pendiente * lx));
            var c = svg('circle', {
                cx: X(lx), cy: Y(ly), r: 4, fill: COLORES[p[3]], 'fill-opacity': .78,
                stroke: 'rgba(0,0,0,.35)', 'stroke-width': .6, tabindex: '0', 'class': 'rel-punto'
            });
            conTip(c, D.nombres[p[0]] + ' · ' + pob(p[1]) + ' hab. · ' + numero(p[2]) + ' ' + ind.unidad +
                ' (' + dec(razon, 2) + ' veces lo esperado)');
            if (p[0] === iFoco) foco = { c: c, x: X(lx), y: Y(ly) }; else gPuntos.appendChild(c);
        });
        s.appendChild(gPuntos);
        if (foco) {
            foco.c.setAttribute('r', 6); foco.c.setAttribute('stroke', COLOR_FOCO); foco.c.setAttribute('stroke-width', 2);
            s.appendChild(foco.c);
            var etiq = texto(foco.x + 9, foco.y - 8, D.pais_foco, { fill: '#fff', 'font-size': 11, 'font-weight': 600 });
            s.appendChild(etiq);
        }
        cont.appendChild(s);

        var l = 'Lectura del filtro actual: en ' + estado.anio + ', la correlacion de Spearman entre poblacion y ' + ind.nombre +
            ' es ' + dec(d.spearman, 2) + ' (Pearson log-log ' + dec(d.pearson_log, 2) + '). ';
        if (d.foco) {
            l += D.pais_foco + ' ocupa el puesto ' + d.foco.puesto + ' de ' + d.foco.de + ' y esta ' +
                (d.foco.razon < 1 ? 'por debajo' : 'por encima') + ' de lo esperado por su tamano (' + dec(d.foco.razon, 2) + ' veces).';
        }
        el('rel-v1-lectura').textContent = l;
    }

    // ---- Visualizacion 2: regiones en base 100 ------------------------------
    function renderV2() {
        var ind = infoInd(estado.ind);
        var series = D.regiones[ind.clave] || [];
        var cont = el('rel-v2'), ley = el('rel-v2-ley');
        vaciar(cont); vaciar(ley);
        el('rel-v2-titulo').textContent = 'Evolucion de ' + ind.nombre + ' por region (base 100 = ' + D.anios[0] + ')';
        if (!series.length) {
            cont.appendChild(crear('p', 'pob-mini', 'No hay series regionales completas para este indicador.'));
            el('rel-v2-sub').textContent = ''; el('rel-v2-lectura').textContent = '';
            return;
        }
        el('rel-v2-sub').textContent = series.length + ' regiones · ' + D.anios[0] + '-' + D.anios[D.anios.length - 1] + ' · cada linea parte de 100 en ' + D.anios[0];

        var W = 640, H = 340, mL = 48, mR = 90, mT = 14, mB = 40;
        var pw = W - mL - mR, ph = H - mT - mB;
        var todos = [];
        series.forEach(function (s) { todos = todos.concat(s.base100); });
        var mn = Math.min.apply(null, todos), mx = Math.max.apply(null, todos);
        var pad = Math.max((mx - mn) * 0.1, 1);
        var lo = Math.floor((mn - pad) / 5) * 5, hi = Math.ceil((mx + pad) / 5) * 5;
        function X(i) { return mL + (D.anios.length === 1 ? 0 : i / (D.anios.length - 1) * pw); }
        function Y(v) { return mT + ph - (v - lo) / (hi - lo) * ph; }

        var s = svg('svg', { viewBox: '0 0 ' + W + ' ' + H, width: '100%', 'aria-hidden': 'true', 'class': 'pob-svg' });
        var paso = Math.max(5, Math.ceil((hi - lo) / 5 / 5) * 5);
        for (var v = lo; v <= hi; v += paso) {
            s.appendChild(svg('line', { x1: mL, x2: mL + pw, y1: Y(v), y2: Y(v), stroke: v === 100 ? 'rgba(255,255,255,.25)' : 'rgba(255,255,255,.07)' }));
            s.appendChild(texto(mL - 8, Y(v) + 3, String(v), { 'text-anchor': 'end' }));
        }
        D.anios.forEach(function (a, i) {
            s.appendChild(texto(X(i), H - 14, String(a), { 'text-anchor': 'middle', fill: String(a) === estado.anio ? '#fff' : 'rgba(244,247,251,.6)', 'font-weight': String(a) === estado.anio ? 700 : 400 }));
        });
        var iSel = D.anios.indexOf(parseInt(estado.anio, 10));
        if (iSel >= 0) s.appendChild(svg('line', { x1: X(iSel), x2: X(iSel), y1: mT, y2: mT + ph, stroke: '#ff6a4d', 'stroke-dasharray': '4 4', 'stroke-width': 1.2 }));

        var ordenadas = series.slice().sort(function (a, b) { return b.base100[b.base100.length - 1] - a.base100[a.base100.length - 1]; });
        // Posiciones verticales de las etiquetas finales, separadas al menos 12 px para que no se pisen.
        var yEtiq = {};
        var previo = -Infinity;
        ordenadas.forEach(function (sr) {
            var y = Math.max(Y(sr.base100[sr.base100.length - 1]) + 3, previo + 12);
            yEtiq[sr.entidad] = y; previo = y;
        });
        ordenadas.forEach(function (sr) {
            var i = series.indexOf(sr), color = COLORES[i % COLORES.length];
            var pts = sr.base100.map(function (v, k) { return X(k) + ',' + Y(v); }).join(' ');
            s.appendChild(svg('polyline', { points: pts, fill: 'none', stroke: color, 'stroke-width': 2.2, 'stroke-linejoin': 'round' }));
            sr.base100.forEach(function (v, k) {
                var c = svg('circle', { cx: X(k), cy: Y(v), r: k === iSel ? 5 : 3.2, fill: color, stroke: 'rgba(0,0,0,.4)', 'stroke-width': .6, tabindex: '0', 'class': 'rel-punto' });
                conTip(c, sr.entidad + ' · ' + D.anios[k] + ': ' + dec(v, 1) + ' (base 100) · valor ' + numero(sr.valores[k]) + ' ' + ind.unidad);
                s.appendChild(c);
            });
            var ult = sr.base100[sr.base100.length - 1];
            s.appendChild(texto(X(sr.base100.length - 1) + 8, yEtiq[sr.entidad], sr.entidad, { fill: color, 'font-size': 10, 'font-weight': 600 }));
            var sp = crear('span'); var sw = crear('i', 'pob-sw'); sw.style.background = color;
            sp.appendChild(sw); sp.appendChild(document.createTextNode(' ' + sr.entidad)); ley.appendChild(sp);
        });
        cont.appendChild(s);

        if (iSel >= 0) {
            var cambios = series.map(function (sr) { return { e: sr.entidad, c: iSel === sr.base100.length - 1 ? sr.cambio_pct : sr.base100[iSel] - 100 }; })
                .sort(function (a, b) { return b.c - a.c; });
            el('rel-v2-lectura').textContent = 'Lectura del filtro actual: hasta ' + estado.anio + ', ' + cambios[0].e + ' acumula ' +
                signo(cambios[0].c, 1) + ' y ' + cambios[cambios.length - 1].e + ' ' + signo(cambios[cambios.length - 1].c, 1) +
                ' en ' + ind.nombre + ' respecto a ' + D.anios[0] + '.';
        }
    }

    // ---- Visualizacion 3: variacion del CO2 mundial y eventos ---------------
    function renderV3() {
        var cont = el('rel-v3');
        vaciar(cont);
        var datos = D.mundo.filter(function (m) { return m.variacion !== null; });
        el('rel-v3-sub').textContent = 'Entidad World · ' + D.anios[0] + '-' + D.anios[D.anios.length - 1] + ' · ' + D.eventos.length + ' eventos documentados';
        if (!datos.length) {
            cont.appendChild(crear('p', 'pob-mini', 'No hay variacion anual del CO2 mundial en el dataset.'));
            return;
        }
        var W = 640, H = 340, mL = 48, mR = 16, mT = 24, mB = 64;
        var pw = W - mL - mR, ph = H - mT - mB;
        var vals = datos.map(function (m) { return m.variacion; });
        var mn = Math.min(0, Math.min.apply(null, vals)), mx = Math.max(0, Math.max.apply(null, vals));
        var lo = Math.floor(mn - 1), hi = Math.ceil(mx + 1);
        function Y(v) { return mT + ph - (v - lo) / (hi - lo) * ph; }
        var banda = pw / datos.length, bw = Math.min(64, banda * 0.55);

        var s = svg('svg', { viewBox: '0 0 ' + W + ' ' + H, width: '100%', 'aria-hidden': 'true', 'class': 'pob-svg' });
        for (var v = lo; v <= hi; v += 1) {
            s.appendChild(svg('line', { x1: mL, x2: mL + pw, y1: Y(v), y2: Y(v), stroke: v === 0 ? 'rgba(255,255,255,.35)' : 'rgba(255,255,255,.06)' }));
            s.appendChild(texto(mL - 8, Y(v) + 3, v + '%', { 'text-anchor': 'end' }));
        }
        datos.forEach(function (m, i) {
            var cx = mL + banda * i + banda / 2;
            var sel = String(m.anio) === estado.anio;
            var y = Y(Math.max(m.variacion, 0)), h = Math.max(Math.abs(Y(m.variacion) - Y(0)), 1.5);
            var r = svg('rect', { x: cx - bw / 2, y: y, width: bw, height: h, rx: 3, fill: sel ? '#ff6a4d' : '#49c7e0', tabindex: '0', 'class': 'pob-col' });
            var evs = eventosAnio(m.anio);
            conTip(r, m.anio + ' · CO2 mundial ' + signo(m.variacion, 2) + ' (' + numero(m.co2) + ' Mt) · ' + evs.length + ' evento(s)');
            s.appendChild(r);
            s.appendChild(texto(cx, m.variacion >= 0 ? y - 6 : y + h + 13, signo(m.variacion, 2), { 'text-anchor': 'middle', fill: '#f4f7fb', 'font-weight': 600 }));
            s.appendChild(texto(cx, mT + ph + 18, String(m.anio), { 'text-anchor': 'middle', fill: sel ? '#fff' : 'rgba(244,247,251,.7)', 'font-size': 11, 'font-weight': sel ? 700 : 400 }));
            evs.forEach(function (e, k) {
                var dx = cx - (evs.length - 1) * 9 + k * 18, dy = mT + ph + 40;
                var rom = svg('path', { d: 'M' + dx + ' ' + (dy - 7) + ' L' + (dx + 7) + ' ' + dy + ' L' + dx + ' ' + (dy + 7) + ' L' + (dx - 7) + ' ' + dy + ' Z', fill: '#ffb454', stroke: 'rgba(0,0,0,.4)', tabindex: '0', 'class': 'rel-evento' });
                conTip(rom, e.fecha + ' · ' + e.evento + ' (' + e.tipo + ')');
                s.appendChild(rom);
            });
        });
        cont.appendChild(s);

        var tb = el('rel-v3-tabla'); vaciar(tb);
        D.eventos.forEach(function (e) {
            var tr = crear('tr', String(e.anio) === estado.anio ? 'rel-fila-sel' : '');
            [[e.fecha, 'mono'], [e.evento], [e.tipo], [e.ambito]].forEach(function (c) { tr.appendChild(crear('td', c[1] || '', c[0])); });
            tb.appendChild(tr);
        });

        var m = mundoAnio(estado.anio), evs2 = eventosAnio(estado.anio);
        el('rel-v3-lectura').textContent = m && m.variacion !== null
            ? 'Lectura del filtro actual: en ' + estado.anio + ' el CO2 mundial vario ' + signo(m.variacion, 2) + ' y hay ' + evs2.length +
              ' evento(s) documentado(s)' + (evs2.length ? ' (' + evs2.map(function (e) { return e.evento.split(' - ')[0]; }).join('; ') + ')' : '') + '.'
            : '';
    }

    // ---- Tabla de apoyo -----------------------------------------------------
    function renderApoyo() {
        el('rel-a-sub').textContent = 'Paises con poblacion e indicador · ' + estado.anio;
        var tb = el('rel-a-tabla'); vaciar(tb);
        D.indicadores.forEach(function (i) {
            var d = (D.dispersion[i.clave] || {})[estado.anio];
            var tr = crear('tr', i.clave === estado.ind ? 'rel-fila-sel' : '');
            if (!d) {
                tr.appendChild(crear('td', '', i.nombre));
                for (var k = 0; k < 5; k++) tr.appendChild(crear('td', 'mono', '-'));
            } else {
                tr.appendChild(crear('td', '', i.nombre + ' (' + i.tipo + ')'));
                [String(d.n), dec(d.spearman, 2), dec(d.pearson_log, 2), dec(d.pendiente, 2),
                 d.foco ? dec(d.foco.razon, 2) + ' veces' : 'sin dato'].forEach(function (t) { tr.appendChild(crear('td', 'mono', t)); });
            }
            tb.appendChild(tr);
        });
    }

    function renderTodo() {
        ocultarTip();
        renderIndicadores(); renderV1(); renderV2(); renderV3(); renderApoyo();
    }

    selAnio.addEventListener('change', function () { estado.anio = selAnio.value; renderTodo(); });
    selInd.addEventListener('change', function () { estado.ind = selInd.value; renderTodo(); });
    el('rel-f-reset').addEventListener('click', function () {
        estado.anio = String(D.anio_ref); estado.ind = D.indicadores[0].clave;
        selAnio.value = estado.anio; selInd.value = estado.ind;
        renderTodo();
    });

    renderTodo();
})();
