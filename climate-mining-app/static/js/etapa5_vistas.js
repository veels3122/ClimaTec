// ClimaTec - Etapa 5 / Analisis multidimensional.
// Las cuatro vistas interactivas del cubo. Cada vista lee su bloque JSON
// (#v1-datos ... #v4-datos), calculado por scripts/multidimensional.py sobre
// clima_limpio.csv, y aplica en el navegador las operaciones OLAP:
//   Vista 1: drill-down / roll-up en la jerarquia Tiempo + slice por serie.
//   Vista 2: drill-down / roll-up Mundo -> Region -> Pais + slice por anio e indicador.
//   Vista 3: slice por indicador + dice por territorios y anios (mapa de calor).
//   Vista 4: tabla dinamica (pivot) con filtros (slice / dice) y totales.
// Sin librerias externas: todo es DOM y SVG. Reutiliza los estilos pob-* de la
// Etapa 4 y los e5-* propios.

(function () {
    'use strict';

    var NS = 'http://www.w3.org/2000/svg';
    var C_FRIO = '#49c7e0', C_CALIDO = '#ff6a4d', C_AMBAR = '#ffb454', C_OK = '#3ddc97';
    var COLORES = [C_FRIO, C_CALIDO, C_AMBAR, C_OK];

    // ---- Utilidades ---------------------------------------------------------
    function el(id) { return document.getElementById(id); }
    function leer(id) { var n = el(id); return n ? JSON.parse(n.textContent) : null; }
    function vaciar(n) { while (n.firstChild) n.removeChild(n.firstChild); }
    function crear(tag, clase, texto) {
        var n = document.createElement(tag);
        if (clase) n.className = clase;
        if (texto !== undefined && texto !== null) n.textContent = texto;
        return n;
    }
    function svg(tag, attrs) {
        var n = document.createElementNS(NS, tag);
        Object.keys(attrs || {}).forEach(function (k) { n.setAttribute(k, attrs[k]); });
        return n;
    }
    function dec(n, d) {
        return Number(n).toLocaleString('es-CO', { minimumFractionDigits: d, maximumFractionDigits: d });
    }
    function auto(n) {
        if (n === null || n === undefined || isNaN(n)) return 'sin dato';
        var a = Math.abs(n);
        if (a >= 1e9) return dec(n / 1e9, 2) + ' mil M';
        if (a >= 1e6) return dec(n / 1e6, 1) + ' M';
        if (a >= 100) return dec(n, 0);
        if (a >= 10) return dec(n, 1);
        return dec(n, 2);
    }
    function pct(n, d) { return dec(n, d === undefined ? 1 : d) + '%'; }
    function signo(n, d, suf) { return (n > 0 ? '+' : '') + dec(n, d === undefined ? 1 : d) + (suf || '%'); }
    function opcion(sel, valor, texto) {
        var o = crear('option', '', texto);
        o.value = valor;
        sel.appendChild(o);
        return o;
    }
    function check(caja, valor, texto, marcado, alCambiar) {
        var l = crear('label', 'e5-check');
        var i = crear('input');
        i.type = 'checkbox';
        i.value = valor;
        i.checked = marcado;
        i.addEventListener('change', alCambiar);
        l.appendChild(i);
        l.appendChild(crear('span', '', texto));
        caja.appendChild(l);
        return i;
    }
    function migas(nodo, pasos) {
        // pasos: [{texto, accion?}] ; el ultimo es el nivel actual.
        vaciar(nodo);
        pasos.forEach(function (p, k) {
            var li = crear('li');
            if (p.accion && k < pasos.length - 1) {
                var b = crear('button', 'e5-miga', p.texto);
                b.type = 'button';
                b.addEventListener('click', p.accion);
                li.appendChild(b);
            } else {
                var s = crear('span', '', p.texto);
                if (k === pasos.length - 1) s.setAttribute('aria-current', 'step');
                li.appendChild(s);
            }
            nodo.appendChild(li);
        });
    }

    // ---- Tooltip comun ------------------------------------------------------
    var tip = crear('div', 'pob-tip');
    tip.setAttribute('role', 'tooltip');
    tip.style.position = 'fixed';
    tip.style.pointerEvents = 'none';
    tip.style.display = 'none';
    tip.style.zIndex = '60';
    document.body.appendChild(tip);
    function mostrarTip(e, texto) {
        tip.textContent = texto;
        tip.style.display = 'block';
        var x = (e.clientX || 0) + 14, y = (e.clientY || 0) + 14;
        if (!e.clientX && e.target && e.target.getBoundingClientRect) {
            var r = e.target.getBoundingClientRect();
            x = r.left + r.width / 2; y = r.top - 8;
        }
        tip.style.left = Math.min(x, window.innerWidth - 260) + 'px';
        tip.style.top = y + 'px';
    }
    function ocultarTip() { tip.style.display = 'none'; }

    // =========================================================================
    // VISTA 1 - Tiempo
    // =========================================================================
    function vistaTemporal(D) {
        var NIVELES = { anio: 'Anio', semestre: 'Semestre', trimestre: 'Trimestre', mes: 'Mes' };
        var selSerie = el('v1-serie');
        var cajaEnts = el('v1-ents');
        var botonesNivel = Array.prototype.slice.call(el('v1-nivel').querySelectorAll('button'));

        // Indicadores mensuales (agrupando sus fuentes) y anuales.
        var mensuales = {};
        D.mensuales.forEach(function (s) { (mensuales[s.indicador] = mensuales[s.indicador] || []).push(s); });
        var gM = crear('optgroup'); gM.label = 'Series mensuales (llegan al nivel Mes)';
        Object.keys(mensuales).sort().forEach(function (i) { opcion(gM, 'm:' + i, i); });
        selSerie.appendChild(gM);
        var gA = crear('optgroup'); gA.label = 'Series anuales (Mundo, Sudamerica, Colombia)';
        Object.keys(D.anuales).sort().forEach(function (i) { opcion(gA, 'a:' + i, i + ' (' + D.anuales[i].unidad + ')'); });
        selSerie.appendChild(gA);

        var DEF = Object.keys(mensuales).indexOf('Anomalia de temperatura global') >= 0
            ? 'm:Anomalia de temperatura global' : selSerie.options[0].value;
        var estado = { serie: DEF, nivel: 'anio', foco: null, activos: null };

        function esMensual() { return estado.serie.indexOf('m:') === 0; }
        function indicador() { return estado.serie.slice(2); }

        function series() {
            // Devuelve [{nombre, unidad, puntos:[{clave, etiqueta, orden, valor, n, anio}]}]
            var ind = indicador();
            if (esMensual()) {
                return mensuales[ind].map(function (s) {
                    var grupos = {};
                    s.puntos.forEach(function (p) {
                        var a = p[0], mes = p[1], v = p[2];
                        if (estado.foco !== null && a !== estado.foco) return;
                        var clave, etq, orden;
                        if (estado.nivel === 'anio') { clave = 'a' + a; etq = String(a); orden = a * 100; }
                        else if (estado.nivel === 'semestre') { var sm = Math.ceil(mes / 6); clave = a + 's' + sm; etq = 'S' + sm + ' ' + a; orden = a * 100 + sm; }
                        else if (estado.nivel === 'trimestre') { var t = Math.ceil(mes / 3); clave = a + 't' + t; etq = 'T' + t + ' ' + a; orden = a * 100 + t; }
                        else { clave = a + 'm' + mes; etq = D.meses[mes - 1] + ' ' + String(a).slice(2); orden = a * 100 + mes; }
                        var g = grupos[clave] || (grupos[clave] = { clave: clave, etiqueta: etq, orden: orden, suma: 0, n: 0, anio: a });
                        g.suma += v; g.n += 1;
                    });
                    var pts = Object.keys(grupos).map(function (k) {
                        var g = grupos[k]; g.valor = g.suma / g.n; return g;
                    }).sort(function (x, y) { return x.orden - y.orden; });
                    return { nombre: s.fuente, unidad: s.unidad, puntos: pts };
                });
            }
            var A = D.anuales[ind];
            return Object.keys(A.series).map(function (ent) {
                return {
                    nombre: ent, unidad: A.unidad,
                    puntos: A.series[ent].map(function (p) {
                        return { clave: 'a' + p[0], etiqueta: String(p[0]), orden: p[0] * 100, valor: p[1], n: 1, anio: p[0] };
                    })
                };
            });
        }

        function prepararChecks() {
            vaciar(cajaEnts);
            var nombres = esMensual()
                ? mensuales[indicador()].map(function (s) { return s.fuente; })
                : Object.keys(D.anuales[indicador()].series);
            estado.activos = {};
            nombres.forEach(function (n) {
                estado.activos[n] = true;
                check(cajaEnts, n, n, true, function (e) { estado.activos[e.target.value] = e.target.checked; pintar(); });
            });
            el('v1-ents-caja').querySelector('span').textContent = esMensual()
                ? 'Fuentes (slice por fuente)' : 'Territorios (slice por geografia)';
        }

        function pintar() {
            var mensual = esMensual();
            botonesNivel.forEach(function (b) {
                var activo = b.dataset.nivel === estado.nivel;
                b.classList.toggle('activo', activo);
                b.setAttribute('aria-checked', activo ? 'true' : 'false');
                b.disabled = !mensual && b.dataset.nivel !== 'anio';
            });
            var todas = series();
            var visibles = todas.filter(function (s) { return estado.activos[s.nombre]; });
            var unidad = todas.length ? todas[0].unidad : '';

            // Ruta (migas): Todos los anios > [anio] > nivel
            var pasos = [{ texto: 'Todos los anios', accion: function () { estado.foco = null; estado.nivel = 'anio'; pintar(); } }];
            if (estado.foco !== null) pasos.push({ texto: String(estado.foco), accion: function () { estado.nivel = 'anio'; estado.foco = null; pintar(); } });
            pasos.push({ texto: 'Nivel ' + NIVELES[estado.nivel] });
            migas(el('v1-migas'), pasos);

            el('v1-titulo').textContent = indicador() + ' por ' + NIVELES[estado.nivel].toLowerCase() +
                (estado.foco !== null ? ' en ' + estado.foco : '');
            el('v1-sub').textContent = mensual
                ? 'Promedio de los meses de cada periodo (' + unidad + '). Medida no aditiva: al subir de nivel se promedia.'
                : 'Valor anual (' + unidad + '). Esta serie no tiene datos mensuales: la jerarquia se detiene en el nivel Anio.';
            el('v1-ayuda').textContent = mensual
                ? 'Drill-down: elige Mes o haz clic en un anio de la grafica. Roll-up: elige un nivel mas alto o usa la ruta.'
                : 'Cambia de territorio con las casillas (slice) para comparar Mundo, Sudamerica y Colombia.';

            // Leyenda
            var ley = el('v1-leyenda'); vaciar(ley);
            visibles.forEach(function (s) {
                var k = todas.indexOf(s);
                var sp = crear('span'); var i = crear('i', 'pob-sw'); i.style.background = COLORES[k % 4];
                sp.appendChild(i); sp.appendChild(document.createTextNode(' ' + s.nombre)); ley.appendChild(sp);
            });

            dibujar(todas, visibles, mensual);
            tabla(visibles);
            lectura(visibles, unidad, mensual);
        }

        function dibujar(todas, visibles, mensual) {
            var caja = el('v1-graf'); vaciar(caja);
            if (!visibles.length) { caja.appendChild(crear('p', 'pob-mini', 'Marca al menos una serie.')); return; }
            var etiquetas = {};
            visibles.forEach(function (s) { s.puntos.forEach(function (p) { etiquetas[p.clave] = p; }); });
            var ejes = Object.keys(etiquetas).map(function (k) { return etiquetas[k]; })
                .sort(function (a, b) { return a.orden - b.orden; });
            var pos = {}; ejes.forEach(function (p, i) { pos[p.clave] = i; });
            var vals = [];
            visibles.forEach(function (s) { s.puntos.forEach(function (p) { vals.push(p.valor); }); });
            var mn = Math.min.apply(null, vals), mx = Math.max.apply(null, vals);
            var pad = (mx - mn) * 0.12 || Math.abs(mx) * 0.1 || 1;
            mn -= pad; mx += pad;
            var W = 760, H = 300, L = 62, R = 16, T = 14, B = 42;
            var s = svg('svg', { viewBox: '0 0 ' + W + ' ' + H, class: 'pob-svg', width: '100%' });
            function X(i) { return ejes.length === 1 ? L + (W - L - R) / 2 : L + i * (W - L - R) / (ejes.length - 1); }
            function Y(v) { return T + (mx - v) / (mx - mn) * (H - T - B); }
            for (var g = 0; g <= 4; g++) {
                var v = mn + (mx - mn) * g / 4, y = Y(v);
                s.appendChild(svg('line', { x1: L, x2: W - R, y1: y, y2: y, class: 'e5-grid' }));
                var t = svg('text', { x: L - 8, y: y + 4, 'text-anchor': 'end', class: 'e5-eje' }); t.textContent = auto(v); s.appendChild(t);
            }
            var paso = Math.ceil(ejes.length / 14);
            ejes.forEach(function (p, i) {
                if (i % paso !== 0 && i !== ejes.length - 1) return;
                var t = svg('text', { x: X(i), y: H - B + 18, 'text-anchor': 'middle', class: 'e5-eje' });
                t.textContent = p.etiqueta; s.appendChild(t);
            });
            visibles.forEach(function (serie) {
                var color = COLORES[todas.indexOf(serie) % 4];
                var d = serie.puntos.map(function (p, i) { return (i ? 'L' : 'M') + X(pos[p.clave]) + ' ' + Y(p.valor); }).join(' ');
                s.appendChild(svg('path', { d: d, fill: 'none', stroke: color, 'stroke-width': 2.2, class: 'e5-linea' }));
                serie.puntos.forEach(function (p) {
                    var drill = mensual && estado.nivel === 'anio';
                    var c = svg('circle', { cx: X(pos[p.clave]), cy: Y(p.valor), r: drill ? 6 : 3.6, fill: color, class: 'e5-punto' + (drill ? ' drill' : '') });
                    var txt = serie.nombre + ' · ' + p.etiqueta + ': ' + auto(p.valor) + ' ' + serie.unidad +
                        (mensual && p.n ? ' (' + p.n + (p.n === 1 ? ' mes)' : ' meses)') : '') + (drill ? ' · clic para ver sus meses' : '');
                    c.setAttribute('tabindex', '0');
                    c.setAttribute('aria-label', txt);
                    c.addEventListener('mousemove', function (e) { mostrarTip(e, txt); });
                    c.addEventListener('mouseleave', ocultarTip);
                    c.addEventListener('focus', function (e) { mostrarTip(e, txt); });
                    c.addEventListener('blur', ocultarTip);
                    if (drill) {
                        var ir = function () { ocultarTip(); estado.foco = p.anio; estado.nivel = 'mes'; pintar(); };
                        c.addEventListener('click', ir);
                        c.addEventListener('keydown', function (e) { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); ir(); } });
                    }
                    s.appendChild(c);
                });
            });
            caja.appendChild(s);
        }

        function tabla(visibles) {
            var th = el('v1-thead'), tb = el('v1-tbody'); vaciar(th); vaciar(tb);
            var tr = crear('tr'); tr.appendChild(crear('th', '', 'Periodo'));
            visibles.forEach(function (s) { tr.appendChild(crear('th', '', s.nombre)); });
            th.appendChild(tr);
            var filas = {};
            visibles.forEach(function (s, k) {
                s.puntos.forEach(function (p) {
                    var f = filas[p.clave] || (filas[p.clave] = { etq: p.etiqueta, orden: p.orden, v: [] });
                    f.v[k] = p.valor;
                });
            });
            Object.keys(filas).map(function (k) { return filas[k]; }).sort(function (a, b) { return a.orden - b.orden; })
                .forEach(function (f) {
                    var r = crear('tr'); r.appendChild(crear('td', '', f.etq));
                    visibles.forEach(function (s, k) { r.appendChild(crear('td', 'mono', f.v[k] === undefined ? '—' : auto(f.v[k]))); });
                    tb.appendChild(r);
                });
        }

        function lectura(visibles, unidad, mensual) {
            var partes = visibles.map(function (s) {
                if (!s.puntos.length) return '';
                var mx = s.puntos[0], mn = s.puntos[0];
                s.puntos.forEach(function (p) { if (p.valor > mx.valor) mx = p; if (p.valor < mn.valor) mn = p; });
                var ini = s.puntos[0], fin = s.puntos[s.puntos.length - 1];
                var aviso = mensual && estado.nivel === 'anio' && fin.n < 12 ? ' (' + fin.etiqueta + ' tiene solo ' + fin.n + ' meses)' : '';
                return s.nombre + ': maximo en ' + mx.etiqueta + ' (' + auto(mx.valor) + ' ' + unidad + '), minimo en ' +
                    mn.etiqueta + ' (' + auto(mn.valor) + '); de ' + ini.etiqueta + ' a ' + fin.etiqueta + ' cambia ' +
                    (fin.valor - ini.valor >= 0 ? '+' : '') + auto(fin.valor - ini.valor) + ' ' + unidad + aviso + '.';
            }).filter(Boolean);
            el('v1-lectura').textContent = partes.join(' ');
        }

        selSerie.value = estado.serie;
        selSerie.addEventListener('change', function () {
            estado.serie = selSerie.value; estado.foco = null;
            if (!esMensual()) estado.nivel = 'anio';
            prepararChecks(); pintar();
        });
        botonesNivel.forEach(function (b) {
            b.addEventListener('click', function () { if (!b.disabled) { estado.nivel = b.dataset.nivel; pintar(); } });
        });
        el('v1-reset').addEventListener('click', function () {
            estado.serie = DEF; estado.nivel = 'anio'; estado.foco = null; selSerie.value = DEF; prepararChecks(); pintar();
        });
        prepararChecks();
        pintar();
    }

    // =========================================================================
    // VISTA 2 - Geografia (Mundo > Region > Pais)
    // =========================================================================
    function vistaTerritorial(D) {
        var selInd = el('v2-ind'), selAnio = el('v2-anio');
        D.indicadores.forEach(function (i) { opcion(selInd, i.clave, i.clave + ' (' + i.unidad + ')'); });
        D.anios.forEach(function (a) { opcion(selAnio, String(a), String(a)); });
        var estado = { ind: D.indicadores[0].clave, anio: String(D.anio_ref), region: null };
        selInd.value = estado.ind; selAnio.value = estado.anio;
        var nombreReg = {}; D.regiones.forEach(function (r) { nombreReg[r.clave] = r.nombre; });
        var maxPaises = 0;
        Object.keys(D.valores[D.indicadores[0].clave] || {}).forEach(function (a) {
            var n = D.valores[D.indicadores[0].clave][a].filter(function (v) { return v !== null; }).length;
            if (n > maxPaises) maxPaises = n;
        });

        function unidad() { for (var i = 0; i < D.indicadores.length; i++) if (D.indicadores[i].clave === estado.ind) return D.indicadores[i].unidad; return ''; }
        function fila() { return (D.valores[estado.ind] || {})[estado.anio] || []; }
        function oficial(ent) { var o = ((D.oficiales[estado.ind] || {})[estado.anio] || {}); return o[ent] === undefined ? null : o[ent]; }

        function kpi(valor, etq, sub, clase) {
            var p = crear('div', 'panel stat' + (clase ? ' ' + clase : ''));
            p.appendChild(crear('div', 'valor', valor));
            p.appendChild(crear('div', 'etiqueta', etq));
            if (sub) p.appendChild(crear('p', 'pob-ind-sub', sub));
            return p;
        }

        function barra(cont, etq, valor, part, maxPart, opciones) {
            var f = crear('div', 'barra-h-fila' + (opciones.foco ? ' warm' : '') + (opciones.resto ? ' e5-resto' : ''));
            f.appendChild(crear('div', 'barra-h-label', etq));
            var tr = crear('div', 'barra-h-track'); var fi = crear('div', 'barra-h-fill'); tr.appendChild(fi); f.appendChild(tr);
            f.appendChild(crear('div', 'barra-h-val pob-val', auto(valor) + ' · ' + pct(part)));
            var txt = etq + ': ' + auto(valor) + ' ' + unidad() + ', ' + pct(part) + ' del total' + (opciones.accion ? ' · clic para ver sus paises' : '');
            f.setAttribute('tabindex', '0');
            f.setAttribute('aria-label', txt);
            if (opciones.accion) {
                f.setAttribute('role', 'button');
                f.classList.add('e5-drill');
                f.addEventListener('click', opciones.accion);
                f.addEventListener('keydown', function (e) { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); opciones.accion(); } });
            }
            f.addEventListener('mousemove', function (e) { mostrarTip(e, txt); });
            f.addEventListener('mouseleave', ocultarTip);
            cont.appendChild(f);
            requestAnimationFrame(function () { fi.style.width = Math.max(0.6, part / maxPart * 100) + '%'; });
        }

        function pintar() {
            ocultarTip();
            var u = unidad(), datos = fila();
            var cont = el('v2-barras'), kp = el('v2-kpis'); vaciar(cont); vaciar(kp);
            var conDato = datos.filter(function (v) { return v !== null; }).length;
            var parcial = conDato < maxPaises * 0.8;

            var pasos = [{ texto: 'Mundo', accion: function () { estado.region = null; pintar(); } }];
            if (estado.region) pasos.push({ texto: nombreReg[estado.region] || estado.region });
            migas(el('v2-migas'), pasos);

            if (!estado.region) {
                // ---- Nivel Region (roll-up desde los paises) ----
                var sumas = {}, total = 0;
                D.paises.forEach(function (p, i) {
                    var v = datos[i]; if (v === null || v === undefined) return;
                    sumas[p.r] = (sumas[p.r] || 0) + v; total += v;
                });
                el('v2-titulo').textContent = estado.ind + ' por region, ' + estado.anio;
                el('v2-sub').textContent = 'Roll-up: cada barra es la suma de los paises de la region (' + u + ').' +
                    (parcial ? ' Atencion: en ' + estado.anio + ' solo ' + conDato + ' paises tienen dato.' : '');
                var mundo = oficial('World');
                kp.appendChild(kpi(auto(total), 'suma de ' + conDato + ' paises (' + u + ')', 'Nivel Mundo calculado desde el cubo', 'cold'));
                kp.appendChild(kpi(mundo === null ? '—' : auto(mundo), 'valor World publicado por la fuente', mundo === null ? 'Sin agregado oficial para este anio' : 'Incluye partidas no asignadas a paises'));
                kp.appendChild(kpi(mundo ? signo((total / mundo - 1) * 100) : '—', 'diferencia suma de paises / World', 'Una diferencia pequena valida el roll-up', 'warm'));
                var regs = D.regiones.map(function (r) { return { r: r, v: sumas[r.clave] || 0 }; })
                    .sort(function (a, b) { return b.v - a.v; });
                var maxP = regs.length ? regs[0].v / total * 100 : 100;
                regs.forEach(function (x) {
                    barra(cont, x.r.nombre, x.v, total ? x.v / total * 100 : 0, maxP || 100, {
                        accion: function () { estado.region = x.r.clave; pintar(); }
                    });
                });
                if (regs.length && total) {
                    var top = regs[0], ult = regs[regs.length - 1];
                    var sa = regs.filter(function (x) { return x.r.clave === 'South America'; })[0];
                    el('v2-lectura').textContent = top.r.nombre + ' concentra ' + pct(top.v / total * 100) + ' del total y ' +
                        ult.r.nombre + ' solo ' + pct(ult.v / total * 100) + '.' +
                        (sa ? ' Sudamerica aporta ' + pct(sa.v / total * 100) + '; haz clic en ella para ver a Colombia.' : '');
                }
            } else {
                // ---- Nivel Pais (drill-down) ----
                var lista = [];
                D.paises.forEach(function (p, i) {
                    if (p.r !== estado.region) return;
                    var v = datos[i]; if (v === null || v === undefined) return;
                    lista.push({ n: p.n, v: v });
                });
                lista.sort(function (a, b) { return b.v - a.v; });
                var tot = lista.reduce(function (s, x) { return s + x.v; }, 0);
                var nom = nombreReg[estado.region];
                el('v2-titulo').textContent = estado.ind + ' en los paises de ' + nom + ', ' + estado.anio;
                el('v2-sub').textContent = 'Drill-down: ' + lista.length + ' paises con dato (' + u + ').' +
                    (parcial ? ' Atencion: anio con cobertura parcial.' : '');
                var ofi = oficial(estado.region);
                kp.appendChild(kpi(auto(tot), 'suma de los paises de ' + nom + ' (' + u + ')', null, 'cold'));
                kp.appendChild(kpi(ofi === null ? '—' : auto(ofi), 'agregado oficial de ' + nom, ofi === null ? null : 'Diferencia: ' + signo((tot / ofi - 1) * 100, 2)));
                var posFoco = -1;
                lista.forEach(function (x, k) { if (x.n === D.foco) posFoco = k; });
                kp.appendChild(posFoco >= 0
                    ? kpi('#' + (posFoco + 1) + ' de ' + lista.length, 'posicion de Colombia', pct(lista[posFoco].v / tot * 100) + ' del total regional', 'warm')
                    : kpi(lista.length ? pct(lista[0].v / tot * 100) : '—', 'participacion del primer pais', lista.length ? lista[0].n : null, 'warm'));
                var MAX = 12, maxP = lista.length ? lista[0].v / tot * 100 : 100;
                lista.slice(0, MAX).forEach(function (x) { barra(cont, x.n, x.v, x.v / tot * 100, maxP, { foco: x.n === D.foco }); });
                if (lista.length > MAX) {
                    var resto = lista.slice(MAX);
                    if (posFoco >= MAX) barra(cont, D.foco, lista[posFoco].v, lista[posFoco].v / tot * 100, maxP, { foco: true });
                    var rv = resto.reduce(function (s, x) { return s + (x.n === D.foco ? 0 : x.v); }, 0);
                    barra(cont, 'Resto (' + (resto.length - (posFoco >= MAX ? 1 : 0)) + ' paises)', rv, rv / tot * 100, maxP, { resto: true });
                }
                if (lista.length) {
                    var acum = 0, n50 = 0;
                    for (var k = 0; k < lista.length; k++) { acum += lista[k].v; n50 = k + 1; if (acum >= tot / 2) break; }
                    el('v2-lectura').textContent = lista[0].n + ' aporta ' + pct(lista[0].v / tot * 100) + ' de ' + nom + '; ' +
                        (n50 === 1 ? 'un solo pais reune' : n50 + ' paises reunen') + ' la mitad del total regional.' +
                        (posFoco >= 0 ? ' Colombia ocupa el puesto ' + (posFoco + 1) + '.' : '');
                } else {
                    el('v2-lectura').textContent = 'No hay datos de este indicador para ' + nom + ' en ' + estado.anio + '.';
                }
            }
        }

        selInd.addEventListener('change', function () { estado.ind = selInd.value; pintar(); });
        selAnio.addEventListener('change', function () { estado.anio = selAnio.value; pintar(); });
        el('v2-reset').addEventListener('click', function () { estado.region = null; pintar(); });
        pintar();
    }

    // =========================================================================
    // VISTA 3 - Mapa de calor Territorio x Anio
    // =========================================================================
    function vistaMapa(D) {
        var selInd = el('v3-ind'), selMed = el('v3-medida');
        D.indicadores.forEach(function (i) { opcion(selInd, i.clave, i.clave + ' (' + i.unidad + ')'); });
        var estado = { ind: D.indicadores[0].clave, medida: 'var', ents: {}, anios: {} };
        selInd.value = estado.ind; selMed.value = estado.medida;
        D.territorios.forEach(function (t) {
            estado.ents[t] = true;
            check(el('v3-ents'), t, t, true, function (e) { estado.ents[e.target.value] = e.target.checked; pintar(); });
        });
        D.anios.forEach(function (a) {
            estado.anios[a] = true;
            check(el('v3-anios'), a, String(a), true, function (e) { estado.anios[e.target.value] = e.target.checked; pintar(); });
        });

        function info() { for (var i = 0; i < D.indicadores.length; i++) if (D.indicadores[i].clave === estado.ind) return D.indicadores[i]; }
        function color(t, divergente) {
            // t en [0,1] (secuencial) o [-1,1] (divergente)
            if (divergente) {
                var a = Math.min(1, Math.abs(t));
                return t >= 0 ? 'rgba(255,106,77,' + (0.12 + a * 0.68) + ')' : 'rgba(73,199,224,' + (0.12 + a * 0.68) + ')';
            }
            return 'rgba(73,199,224,' + (0.08 + t * 0.72) + ')';
        }

        function pintar() {
            var I = info(), datos = D.datos[estado.ind] || {};
            var esPct = I.unidad === '%';
            var ents = D.territorios.filter(function (t) { return estado.ents[t]; });
            var anios = D.anios.filter(function (a) { return estado.anios[a]; });
            var tabla = el('v3-tabla'); vaciar(tabla);
            var med = estado.medida;
            var a0 = anios[0];

            function valor(t, a) {
                var v = (datos[t] || {})[a];
                if (v === undefined) return null;
                if (med === 'valor') return v;
                if (med === 'var') {
                    var b = (datos[t] || {})[a0];
                    if (b === undefined || b === null) return null;
                    if (esPct) return v - b;
                    return b === 0 ? null : (v / b - 1) * 100;
                }
                var w = (datos['Mundo'] || {})[a];
                return w ? v / w * 100 : null;
            }
            function fmt(v) {
                if (v === null) return '—';
                if (med === 'valor') return auto(v);
                if (med === 'var') return esPct ? signo(v, 1, ' pp') : signo(v);
                return dec(v, 0);
            }

            el('v3-titulo').textContent = estado.ind + ' · ' + selMed.options[selMed.selectedIndex].text.toLowerCase();
            el('v3-sub').textContent = med === 'valor' ? 'Valores en ' + I.unidad + ' tal como los publica la fuente para cada territorio.'
                : med === 'var' ? (esPct ? 'Diferencia en puntos porcentuales frente a ' + a0 + '.' : 'Cambio porcentual frente a ' + a0 + ', el primer anio del corte.')
                    : 'Cada celda dividida entre el valor del Mundo en el mismo anio × 100.';

            if (!ents.length || !anios.length) {
                tabla.appendChild(crear('caption', 'pob-mini', 'Marca al menos un territorio y un anio para formar el subcubo.'));
                el('v3-lectura').textContent = ''; vaciar(el('v3-escala'));
                return;
            }
            var vals = [];
            ents.forEach(function (t) { anios.forEach(function (a) { var v = valor(t, a); if (v !== null) vals.push(v); }); });
            var mn = Math.min.apply(null, vals), mx = Math.max.apply(null, vals);
            var lim = Math.max(Math.abs(mn), Math.abs(mx)) || 1;
            var divergente = med === 'var';

            var th = crear('thead'), tr = crear('tr');
            tr.appendChild(crear('th', '', 'Territorio'));
            anios.forEach(function (a) { tr.appendChild(crear('th', '', String(a))); });
            th.appendChild(tr); tabla.appendChild(th);
            var tb = crear('tbody');
            var mejor = null, peor = null;
            ents.forEach(function (t) {
                var r = crear('tr');
                r.appendChild(crear('th', t === 'Colombia' ? 'e5-foco' : '', t));
                anios.forEach(function (a) {
                    var v = valor(t, a), td = crear('td', 'mono', fmt(v));
                    if (v !== null) {
                        var x;
                        if (divergente) x = v / lim;
                        else if (med === 'valor' && mn >= 0) x = Math.sqrt((v - mn) / ((mx - mn) || 1));
                        else x = (v - mn) / ((mx - mn) || 1);
                        td.style.background = color(x, divergente);
                        td.title = t + ' · ' + a + ': ' + fmt(v);
                        if (!(med === 'var' && String(a) === String(a0)) && !(med === 'indice' && t === 'Mundo')) {
                            if (!mejor || v > mejor.v) mejor = { t: t, a: a, v: v };
                            if (!peor || v < peor.v) peor = { t: t, a: a, v: v };
                        }
                    }
                    r.appendChild(td);
                });
                tb.appendChild(r);
            });
            tabla.appendChild(tb);

            var esc = el('v3-escala'); vaciar(esc);
            esc.appendChild(crear('span', '', divergente ? fmt(-lim) : fmt(mn)));
            var barraEsc = crear('i', divergente ? 'div' : 'sec'); esc.appendChild(barraEsc);
            esc.appendChild(crear('span', '', divergente ? fmt(lim) : fmt(mx)));

            var celdas = ents.length * anios.length;
            var txt = 'Subcubo de ' + ents.length + ' territorios × ' + anios.length + ' anios (' + celdas + ' celdas). ';
            if (mejor && peor) {
                txt += 'Valor mas alto: ' + mejor.t + ' en ' + mejor.a + ' (' + fmt(mejor.v) + '); mas bajo: ' + peor.t + ' en ' + peor.a + ' (' + fmt(peor.v) + ').';
            }
            el('v3-lectura').textContent = txt;
        }

        selInd.addEventListener('change', function () { estado.ind = selInd.value; pintar(); });
        selMed.addEventListener('change', function () { estado.medida = selMed.value; pintar(); });
        el('v3-reset').addEventListener('click', function () {
            estado.ind = D.indicadores[0].clave; estado.medida = 'var'; selInd.value = estado.ind; selMed.value = 'var';
            Array.prototype.forEach.call(document.querySelectorAll('#v3-ents input, #v3-anios input'), function (i) { i.checked = true; });
            D.territorios.forEach(function (t) { estado.ents[t] = true; });
            D.anios.forEach(function (a) { estado.anios[a] = true; });
            pintar();
        });
        pintar();
    }

    // =========================================================================
    // VISTA 4 - Tabla dinamica
    // =========================================================================
    function vistaPivot(D) {
        var K = D.claves, NK = K.length;
        var iN = NK, iAT = NK + 1, iZ = NK + 2, iNZ = NK + 3, iV = NK + 4;
        var selF = el('v4-filas'), selC = el('v4-cols'), selM = el('v4-medida');
        K.forEach(function (k) { opcion(selF, k, D.etiquetas[k]); });
        opcion(selC, '', '(ninguna)');
        K.forEach(function (k) { opcion(selC, k, D.etiquetas[k]); });
        var estado = { filas: 'nivel_geografico', cols: 'categoria', medida: 'pat', filtros: {} };
        selF.value = estado.filas; selC.value = estado.cols; selM.value = estado.medida;

        var cajaF = el('v4-filtros');
        var selsFiltro = {};
        K.forEach(function (k) {
            estado.filtros[k] = -1;
            var l = crear('label', 'pob-campo e5-filtro');
            l.appendChild(crear('span', '', D.etiquetas[k]));
            var s = crear('select');
            opcion(s, '-1', 'Todos');
            D.miembros[k].forEach(function (m, i) { opcion(s, String(i), m); });
            s.addEventListener('change', function () { estado.filtros[k] = parseInt(s.value, 10); pintar(); });
            l.appendChild(s); cajaF.appendChild(l); selsFiltro[k] = s;
        });
        var reset = crear('button', 'pob-reset', 'Quitar filtros'); reset.type = 'button';
        reset.addEventListener('click', function () {
            K.forEach(function (k) { estado.filtros[k] = -1; selsFiltro[k].value = '-1'; }); pintar();
        });
        cajaF.appendChild(reset);

        function base() { return { n: 0, at: 0, z: 0, nz: 0, v: 0 }; }
        function sumar(b, c) { b.n += c[iN]; b.at += c[iAT]; b.z += c[iZ]; b.nz += c[iNZ]; b.v += c[iV]; }
        function indicadorFijo() {
            var f = estado.filtros.indicador;
            if (f >= 0) return D.miembros.indicador[f];
            if (estado.filas === 'indicador' || estado.cols === 'indicador') return '*';
            return null;
        }
        function medida(b, ind) {
            if (!b || !b.n) return null;
            switch (estado.medida) {
                case 'n': return b.n;
                case 'at': return b.at;
                case 'pat': return b.at / b.n * 100;
                case 'z': return b.nz ? b.z / b.nz : null;
                case 'v':
                    if (!ind || ind === '*') return null;
                    return D.agregacion[ind] === 'suma' ? b.v : b.v / b.n;
            }
            return null;
        }
        function fmt(v) {
            if (v === null) return '—';
            if (estado.medida === 'n' || estado.medida === 'at') return dec(v, 0);
            if (estado.medida === 'pat') return pct(v);
            if (estado.medida === 'z') return dec(v, 2);
            return auto(v);
        }

        function pintar() {
            if (estado.cols === estado.filas) { estado.cols = ''; selC.value = ''; }
            var kf = K.indexOf(estado.filas), kc = estado.cols ? K.indexOf(estado.cols) : -1;
            var celdas = {}, totF = {}, totC = {}, gran = base();
            D.celdas.forEach(function (c) {
                for (var j = 0; j < NK; j++) { var f = estado.filtros[K[j]]; if (f >= 0 && c[j] !== f) return; }
                var rf = c[kf], rc = kc >= 0 ? c[kc] : 0;
                var cl = rf + '|' + rc;
                sumar(celdas[cl] || (celdas[cl] = base()), c);
                sumar(totF[rf] || (totF[rf] = base()), c);
                sumar(totC[rc] || (totC[rc] = base()), c);
                sumar(gran, c);
            });
            var filas = Object.keys(totF).map(Number).sort(function (a, b) { return a - b; });
            var cols = Object.keys(totC).map(Number).sort(function (a, b) { return a - b; });

            // Indicador de cada celda (para la medida Valor cuando el indicador es eje).
            var ind = indicadorFijo();
            function indCelda(rf, rc) {
                if (ind !== '*') return ind;
                if (estado.filas === 'indicador') return D.miembros.indicador[rf];
                if (estado.cols === 'indicador') return D.miembros.indicador[rc];
                return null;
            }

            // Avisos
            var aviso = '';
            if (estado.medida === 'v') {
                if (!ind) aviso = 'Para ver el valor elige un indicador en los filtros o ponlo como fila o columna: sumar Mt de CO2 con porcentajes no tiene sentido.';
                else if (estado.filtros.nivel_geografico < 0 && estado.filas !== 'nivel_geografico' && estado.cols !== 'nivel_geografico')
                    aviso = 'Atencion: el filtro deja paises, regiones y el mundo juntos, asi que una misma emision se cuenta varias veces. Filtra «Nivel geografico».';
                else if (ind === '*') aviso = 'Los totales mezclan indicadores distintos y se ocultan.';
            }
            el('v4-aviso').textContent = aviso;

            var tabla = el('v4-tabla'); vaciar(tabla);
            var th = crear('thead'), tr = crear('tr');
            tr.appendChild(crear('th', '', D.etiquetas[estado.filas] + (kc >= 0 ? ' \\ ' + D.etiquetas[estado.cols] : '')));
            if (kc >= 0) cols.forEach(function (c) { tr.appendChild(crear('th', '', D.miembros[estado.cols][c])); });
            tr.appendChild(crear('th', 'e5-total', kc >= 0 ? 'Total fila' : 'Valor'));
            th.appendChild(tr); tabla.appendChild(th);

            var maximo = 0, top = null;
            filas.forEach(function (rf) {
                cols.forEach(function (rc) {
                    var v = medida(celdas[rf + '|' + rc], indCelda(rf, rc));
                    if (v !== null && Math.abs(v) > maximo) maximo = Math.abs(v);
                    if (v !== null && (!top || v > top.v)) top = { v: v, f: rf, c: rc };
                });
            });
            var ocultarTotales = estado.medida === 'v' && ind === '*';
            var tb = crear('tbody');
            filas.forEach(function (rf) {
                var r = crear('tr');
                r.appendChild(crear('th', '', D.miembros[estado.filas][rf]));
                if (kc >= 0) cols.forEach(function (rc) {
                    var v = medida(celdas[rf + '|' + rc], indCelda(rf, rc));
                    var td = crear('td', 'mono', fmt(v));
                    if (v !== null && maximo) td.style.background = 'rgba(73,199,224,' + (0.05 + Math.abs(v) / maximo * 0.55) + ')';
                    r.appendChild(td);
                });
                var vt = ocultarTotales && kc >= 0 ? null : medida(totF[rf], estado.filas === 'indicador' ? D.miembros.indicador[rf] : (ind === '*' ? null : ind));
                var tdT = crear('td', 'mono e5-total', fmt(vt));
                if (kc < 0 && vt !== null && maximo) tdT.style.background = 'rgba(73,199,224,' + (0.05 + Math.abs(vt) / maximo * 0.55) + ')';
                r.appendChild(tdT);
                tb.appendChild(r);
            });
            tabla.appendChild(tb);
            if (kc >= 0 || filas.length > 1) {
                var tf = crear('tfoot'), r2 = crear('tr');
                r2.appendChild(crear('th', '', 'Total'));
                if (kc >= 0) cols.forEach(function (rc) {
                    r2.appendChild(crear('td', 'mono', fmt(ocultarTotales && estado.cols !== 'indicador' ? null
                        : medida(totC[rc], estado.cols === 'indicador' ? D.miembros.indicador[rc] : (ind === '*' ? null : ind)))));
                });
                r2.appendChild(crear('td', 'mono e5-total', fmt(ocultarTotales ? null : medida(gran, ind === '*' ? null : ind))));
                tf.appendChild(r2); tabla.appendChild(tf);
            }

            var nomM = selM.options[selM.selectedIndex].text.replace(' (elige un indicador)', '');
            el('v4-titulo').textContent = nomM + ' por ' + D.etiquetas[estado.filas].toLowerCase() +
                (kc >= 0 ? ' y ' + D.etiquetas[estado.cols].toLowerCase() : '');
            var filtrosTxt = K.filter(function (k) { return estado.filtros[k] >= 0; })
                .map(function (k) { return D.etiquetas[k] + ' = ' + D.miembros[k][estado.filtros[k]]; });
            el('v4-sub').textContent = dec(gran.n, 0) + ' hechos en el subcubo' + (filtrosTxt.length ? ' · ' + filtrosTxt.join(' · ') : ' · sin filtros') +
                (estado.medida === 'v' && ind && ind !== '*' ? ' · unidad: ' + (D.unidades[ind] || '') + ', se agrega con ' + D.agregacion[ind] : '');
            el('v4-lectura').textContent = top && !(estado.medida === 'v' && !ind)
                ? 'Celda con el valor mas alto: ' + D.miembros[estado.filas][top.f] + (kc >= 0 ? ' × ' + D.miembros[estado.cols][top.c] : '') + ' (' + fmt(top.v) + ').'
                : '';
        }

        selF.addEventListener('change', function () { estado.filas = selF.value; pintar(); });
        selC.addEventListener('change', function () { estado.cols = selC.value; pintar(); });
        selM.addEventListener('change', function () { estado.medida = selM.value; pintar(); });
        el('v4-swap').addEventListener('click', function () {
            if (!estado.cols) return;
            var t = estado.filas; estado.filas = estado.cols; estado.cols = t;
            selF.value = estado.filas; selC.value = estado.cols; pintar();
        });
        pintar();
    }

    // ---- Arranque -----------------------------------------------------------
    var d1 = leer('v1-datos'); if (d1) vistaTemporal(d1);
    var d2 = leer('v2-datos'); if (d2) vistaTerritorial(d2);
    var d3 = leer('v3-datos'); if (d3) vistaMapa(d3);
    var d4 = leer('v4-datos'); if (d4) vistaPivot(d4);
})();
