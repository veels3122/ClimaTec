// ClimaTec - Etapa 4 / Dimension Territorial.
// Dibuja los indicadores y las tres visualizaciones a partir del JSON que
// imprime la plantilla (#ter-datos), calculado en scripts/territorial.py sobre
// clima_limpio.csv. No usa librerias externas ni imagenes: todo es DOM/SVG.
// Dos filtros: Anio (afecta indicadores y las 3 visualizaciones) e Indicador a
// repartir (afecta los indicadores y las visualizaciones 1 y 2).
// Reutiliza los estilos pob-* de la dimension poblacional para que la Etapa 4
// tenga una identidad visual unica.

(function () {
    'use strict';

    var nodoDatos = document.getElementById('ter-datos');
    if (!nodoDatos) return;
    var D = JSON.parse(nodoDatos.textContent);

    var NS = 'http://www.w3.org/2000/svg';
    var C_FRIO = '#49c7e0', C_CALIDO = '#ff6a4d', C_AMBAR = '#ffb454';

    // ---- Formato (es-CO: punto de miles, coma decimal) ----------------------
    function dec(n, d) {
        return n.toLocaleString('es-CO', { minimumFractionDigits: d, maximumFractionDigits: d });
    }
    function pct(n, d) { return dec(n, d === undefined ? 1 : d) + '%'; }
    function valor(n, unidad) {
        var d = Math.abs(n) >= 100 ? 0 : (Math.abs(n) >= 10 ? 1 : 2);
        return dec(n, d) + ' ' + unidad;
    }
    function minus(t) { return t.charAt(0).toLowerCase() + t.slice(1); }
    function pctChico(n) { return n < 0.001 ? '< 0,001%' : pct(n, 3); }
    function el(id) { return document.getElementById(id); }
    function vaciar(nodo) { while (nodo.firstChild) nodo.removeChild(nodo.firstChild); }
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

    // ---- Estado y filtros ---------------------------------------------------
    var IND_DEF = D.indicadores[0].clave;
    var estado = { anio: String(D.anio_ref), ind: IND_DEF };
    var selAnio = el('ter-f-anio');
    var selInd = el('ter-f-ind');

    D.anios.forEach(function (a) {
        var o = crear('option', '', String(a));
        o.value = String(a);
        selAnio.appendChild(o);
    });
    selAnio.value = estado.anio;
    D.indicadores.forEach(function (i) {
        var o = crear('option', '', i.nombre + ' (' + i.unidad + ')');
        o.value = i.clave;
        selInd.appendChild(o);
    });
    selInd.value = estado.ind;

    function nombreInd(clave) {
        for (var i = 0; i < D.indicadores.length; i++) {
            if (D.indicadores[i].clave === clave) return D.indicadores[i].nombre;
        }
        return clave;
    }
    // Si el indicador no tiene datos para el anio elegido, se usa el ultimo disponible.
    function datosActuales() {
        var por = D.datos[estado.ind] || {};
        if (por[estado.anio]) return por[estado.anio];
        var ks = Object.keys(por).sort();
        return por[ks[ks.length - 1]];
    }

    // ---- Tooltip ------------------------------------------------------------
    var tip = crear('div', 'pob-tip');
    tip.setAttribute('role', 'tooltip');
    tip.hidden = true;
    document.body.appendChild(tip);
    function mostrarTip(ev, texto) {
        tip.textContent = texto;
        tip.hidden = false;
        var x = ev.clientX + 14, y = ev.clientY + 14;
        var w = tip.offsetWidth, h = tip.offsetHeight;
        if (x + w > window.innerWidth - 8) x = ev.clientX - w - 14;
        if (y + h > window.innerHeight - 8) y = ev.clientY - h - 14;
        tip.style.left = x + 'px';
        tip.style.top = y + 'px';
    }
    function ocultarTip() { tip.hidden = true; }
    function conTip(nodo, texto) {
        nodo.addEventListener('mousemove', function (ev) { mostrarTip(ev, texto); });
        nodo.addEventListener('mouseleave', ocultarTip);
        nodo.addEventListener('focus', function () {
            var r = nodo.getBoundingClientRect();
            mostrarTip({ clientX: r.left + r.width / 2, clientY: r.top }, texto);
        });
        nodo.addEventListener('blur', ocultarTip);
    }

    // Barra horizontal animada (mismo estilo que la dimension poblacional).
    function filaBarra(cont, etiqueta, ancho, texto, tipTexto, clase) {
        var fila = crear('div', 'barra-h-fila' + (clase ? ' ' + clase : ''));
        fila.tabIndex = 0;
        fila.appendChild(crear('div', 'barra-h-label', etiqueta));
        var track = crear('div', 'barra-h-track');
        var fill = crear('div', 'barra-h-fill');
        fill.style.width = '0%';
        track.appendChild(fill);
        fila.appendChild(track);
        fila.appendChild(crear('div', 'barra-h-val pob-val', texto));
        cont.appendChild(fila);
        conTip(fila, tipTexto);
        requestAnimationFrame(function () {
            requestAnimationFrame(function () { fill.style.width = Math.max(ancho, 1.2) + '%'; });
        });
        return fila;
    }

    // ---- Indicadores --------------------------------------------------------
    function renderIndicadores() {
        var t = datosActuales();
        var r = t.regiones[0];
        el('ter-i1-valor').textContent = pct(r.pct);
        el('ter-i1-etq').textContent = 'de ' + minus(nombreInd(estado.ind)) + ' se concentra en ' + r.entidad;
        el('ter-i1-sub').textContent = 'Region principal entre 6 · ' + valor(r.valor, t.unidad) + ' · ' + t.anio;

        el('ter-i2-valor').textContent = pct(t.top10_pct);
        el('ter-i2-sub').textContent = 'Bastan ' + t.n50 + ' paises para la mitad y ' + t.n80 + ' para el 80% · ' +
            t.paises + ' paises con dato';

        var c = t.colombia;
        if (c) {
            el('ter-i3-valor').textContent = '#' + c.rank;
            el('ter-i3-etq').textContent = 'posicion de Colombia entre ' + t.paises + ' paises';
            el('ter-i3-sub').textContent = pct(c.pct, 2) + ' del total de paises' +
                (c.pct_sa !== null ? ' · ' + pct(c.pct_sa) + ' de Sudamerica' : '');
        } else {
            el('ter-i3-valor').textContent = '-';
            el('ter-i3-sub').textContent = 'Colombia no tiene dato para este filtro.';
        }
    }

    // ---- Visualizacion 1: participacion por region --------------------------
    function renderV1() {
        var t = datosActuales();
        var cont = el('ter-v1');
        vaciar(cont);
        el('ter-v1-titulo').textContent = 'Participacion de cada region en ' + minus(nombreInd(estado.ind));
        el('ter-v1-sub').textContent = 'Suma de las 6 regiones: ' + valor(t.suma_regiones, t.unidad) + ' · ' + t.anio;
        var max = t.regiones[0].pct || 1;
        t.regiones.forEach(function (r, i) {
            filaBarra(cont, r.entidad, 100 * r.pct / max, pct(r.pct) + ' · ' + valor(r.valor, t.unidad),
                r.entidad + ': ' + valor(r.valor, t.unidad) + ' (' + pct(r.pct, 2) + ')',
                r.entidad === 'Sudamerica' ? 'warm' : '');
        });
        var sa = t.regiones.filter(function (r) { return r.entidad === 'Sudamerica'; })[0];
        var tres = t.regiones[0].pct + t.regiones[1].pct + t.regiones[2].pct;
        el('ter-v1-lectura').textContent = 'Lectura del filtro actual: en ' + t.anio + ', ' + t.regiones[0].entidad +
            ', ' + t.regiones[1].entidad + ' y ' + t.regiones[2].entidad + ' suman ' + pct(tres) +
            '; Sudamerica (resaltada) aporta ' + (sa ? pct(sa.pct) : 'sin dato') + ' y ocupa el puesto ' +
            (t.regiones.indexOf(sa) + 1) + ' de 6.';
    }

    // ---- Visualizacion 2: top 10 paises, resto y Colombia -------------------
    function renderV2() {
        var t = datosActuales();
        var cont = el('ter-v2');
        vaciar(cont);
        el('ter-v2-titulo').textContent = 'Paises con mayor ' + minus(nombreInd(estado.ind)) + ' y posicion de Colombia';
        el('ter-v2-sub').textContent = t.paises + ' paises con dato · total de paises ' + valor(t.total_paises, t.unidad) + ' · ' + t.anio;
        var max = t.top[0].pct || 1;
        t.top.forEach(function (p, i) {
            filaBarra(cont, (i + 1) + '. ' + p.entidad, 100 * p.pct / max, pct(p.pct) + ' · ' + valor(p.valor, t.unidad),
                p.entidad + ': ' + valor(p.valor, t.unidad) + ' (' + pct(p.pct, 2) + ')',
                p.entidad === 'Colombia' ? 'warm' : '');
        });
        var resto = filaBarra(cont, 'Resto (' + t.resto.paises + ' paises)', 100 * t.resto.pct / max,
            pct(t.resto.pct) + ' · ' + valor(t.resto.valor, t.unidad),
            'Resto de paises: ' + valor(t.resto.valor, t.unidad) + ' (' + pct(t.resto.pct, 2) + ')');
        resto.style.opacity = '.7';
        var c = t.colombia;
        if (c && c.rank > 10) {
            filaBarra(cont, c.rank + '. Colombia', 100 * c.pct / max, pct(c.pct, 2) + ' · ' + valor(c.valor, t.unidad),
                'Colombia: puesto ' + c.rank + ', ' + valor(c.valor, t.unidad) + ' (' + pct(c.pct, 3) + ')', 'warm');
        }

        var tb = el('ter-v2-menores');
        vaciar(tb);
        t.menores.forEach(function (m) {
            var tr = crear('tr');
            tr.appendChild(crear('td', '', m.entidad));
            tr.appendChild(crear('td', 'mono', valor(m.valor, t.unidad)));
            tr.appendChild(crear('td', 'mono', pctChico(m.pct)));
            tb.appendChild(tr);
        });
        if (t.ceros > 0) {
            var tr = crear('tr', 'pob-fila-resto');
            var td = crear('td', '', t.ceros + ' territorio(s) reportan 0 y no se incluyen en esta lista.');
            td.colSpan = 3;
            tr.appendChild(td);
            tb.appendChild(tr);
        }

        el('ter-v2-lectura').textContent = 'Lectura del filtro actual: ' + t.top[0].entidad + ' aporta ' + pct(t.top[0].pct) +
            ' y los 10 primeros ' + pct(t.top10_pct) + '; ' + t.n50 + ' paises suman la mitad del total.' +
            (c ? ' Colombia ocupa el puesto ' + c.rank + ' con ' + pct(c.pct, 2) + '.' : '');
    }

    // ---- Visualizacion 3: Colombia y Sudamerica, mundo = 100 ----------------
    function renderV3() {
        var filas = D.comparacion[estado.anio] || D.comparacion[String(D.anio_ref)];
        var cont = el('ter-v3');
        vaciar(cont);
        el('ter-v3-sub').textContent = 'Indicadores per capita y de participacion · ' + estado.anio;

        var maxIdx = Math.max(150, Math.max.apply(null, filas.map(function (f) { return Math.max(f.idx_col, f.idx_sa); })));
        var tope = Math.ceil(maxIdx / 50) * 50;
        var W = 560, H = 290, mI = 42, mD = 10, mS = 24, mInf = 46;
        var ancho = W - mI - mD, alto = H - mS - mInf;
        var s = svg('svg', { viewBox: '0 0 ' + W + ' ' + H, width: '100%', 'aria-hidden': 'true', 'class': 'pob-svg' });
        function y(v) { return mS + alto - alto * v / tope; }

        for (var v = 0; v <= tope; v += 50) {
            s.appendChild(svg('line', { x1: mI, x2: W - mD, y1: y(v), y2: y(v), stroke: 'rgba(255,255,255,.08)' }));
            var t = svg('text', { x: mI - 8, y: y(v) + 4, 'text-anchor': 'end', fill: 'rgba(244,247,251,.48)', 'font-size': 10 });
            t.textContent = String(v);
            s.appendChild(t);
        }
        // Linea de referencia: mundo = 100
        s.appendChild(svg('line', { x1: mI, x2: W - mD, y1: y(100), y2: y(100), stroke: C_FRIO, 'stroke-width': 2, 'stroke-dasharray': '6 4' }));
        var tm = svg('text', { x: mI + 4, y: y(100) - 6, 'text-anchor': 'start', fill: C_FRIO, 'font-size': 10, 'font-weight': 600 });
        tm.textContent = 'Mundo = 100';
        s.appendChild(tm);

        var n = filas.length, banda = ancho / n, bw = Math.min(30, banda * 0.32);
        filas.forEach(function (f, i) {
            var cx = mI + banda * i + banda / 2;
            [
                { v: f.idx_col, x: cx - bw - 2, color: C_CALIDO, nom: 'Colombia', real: f.colombia },
                { v: f.idx_sa, x: cx + 2, color: C_AMBAR, nom: 'Sudamerica', real: f.sudamerica }
            ].forEach(function (sr) {
                var h = Math.max(alto * sr.v / tope, 1.5);
                var r = svg('rect', { x: sr.x, y: mS + alto - h, width: bw, height: h, rx: 3, fill: sr.color, tabindex: '0', 'class': 'pob-col' });
                s.appendChild(r);
                conTip(r, f.indicador + ' · ' + sr.nom + ': ' + dec(sr.real, f.dec) + ' ' + f.unidad + ' (' + dec(sr.v, 0) + ' si mundo = 100)');
                var lab = svg('text', { x: sr.x + bw / 2, y: mS + alto - h - 5, 'text-anchor': 'middle', fill: '#f4f7fb', 'font-size': 10, 'font-weight': 600 });
                lab.textContent = dec(sr.v, 0);
                s.appendChild(lab);
            });
            var xl = svg('text', { x: cx, y: H - mInf + 20, 'text-anchor': 'middle', fill: 'rgba(244,247,251,.72)', 'font-size': 11 });
            xl.textContent = f.indicador;
            s.appendChild(xl);
        });
        cont.appendChild(s);

        var tb = el('ter-v3-tabla');
        vaciar(tb);
        filas.forEach(function (f) {
            var tr = crear('tr');
            [[f.indicador], [dec(f.colombia, f.dec) + ' ' + f.unidad, 'mono'], [dec(f.sudamerica, f.dec) + ' ' + f.unidad, 'mono'],
             [dec(f.mundo, f.dec) + ' ' + f.unidad, 'mono'], [pct(f.idx_col, 0), 'mono']]
                .forEach(function (c) { tr.appendChild(crear('td', c[1] || '', c[0])); });
            tb.appendChild(tr);
        });

        var pc = filas[0];
        el('ter-v3-lectura').textContent = 'Lectura del filtro actual: en ' + estado.anio + ' Colombia emite ' +
            dec(pc.colombia, 2) + ' ' + pc.unidad + ', ' + pct(pc.idx_col, 0) + ' del promedio mundial; Sudamerica ' +
            pct(pc.idx_sa, 0) + '. Las barras por encima de la linea indican valores mayores que el promedio mundial.';
    }

    function renderTodo() {
        ocultarTip();
        renderIndicadores();
        renderV1();
        renderV2();
        renderV3();
    }

    selAnio.addEventListener('change', function () { estado.anio = selAnio.value; renderTodo(); });
    selInd.addEventListener('change', function () { estado.ind = selInd.value; renderTodo(); });
    el('ter-f-reset').addEventListener('click', function () {
        estado.anio = String(D.anio_ref); estado.ind = IND_DEF;
        selAnio.value = estado.anio; selInd.value = estado.ind;
        renderTodo();
    });

    renderTodo();
})();
