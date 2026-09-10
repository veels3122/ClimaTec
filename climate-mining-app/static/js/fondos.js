// ClimaTec — fondos animados por seccion (Definicion y Recoleccion de Datos).
// Un pequeno "motor" comun (resize con devicePixelRatio + requestAnimationFrame,
// apagado si el usuario pide "reduced motion") y una funcion de dibujo por
// seccion, elegida segun el atributo data-fondo del .page-hero. Cada seccion
// nueva que se integre repite el mismo patron: una metafora visual propia,
// ligada a su contenido real (nunca un fondo generico repetido).
// Todo en Canvas 2D puro: sin librerias, sin video, sin imagenes externas.

(function () {
    'use strict';

    const REDUCIDO = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    const PALETA = {
        frio: '#49c7e0',
        calido: '#ff6a4d',
        ambar: '#ffb454',
        ok: '#3ddc97',
        morado: '#c9b6ff',
        blanco: 'rgba(255,255,255,',
    };

    function motor(canvas, dibujar, { fija = false } = {}) {
        const ctx = canvas.getContext('2d');
        let w = 0, h = 0, dpr = Math.min(window.devicePixelRatio || 1, 2);

        function medir() {
            const rect = fija
                ? { width: window.innerWidth, height: window.innerHeight }
                : canvas.parentElement.getBoundingClientRect();
            w = Math.max(1, Math.round(rect.width));
            h = Math.max(1, Math.round(rect.height));
            canvas.width = w * dpr;
            canvas.height = h * dpr;
            ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        }
        medir();
        window.addEventListener('resize', medir);

        let inicio = performance.now();
        function frame(ahora) {
            // Math.max(0, ...): el timestamp que entrega requestAnimationFrame
            // puede corresponder a un instante ANTERIOR al performance.now()
            // que capturamos en "inicio" (es una particularidad conocida del
            // primer frame). Sin este clamp, "t" podia salir levemente
            // negativo una sola vez y algunas formas (radios de circulo,
            // etc.) recibian un valor negativo y Canvas2D lanzaba una
            // excepcion ("radius provided is negative").
            const t = Math.max(0, (ahora - inicio) / 1000);
            dibujar(ctx, w, h, t);
            if (!REDUCIDO) requestAnimationFrame(frame);
        }
        if (REDUCIDO) {
            dibujar(ctx, w, h, 0);
        } else {
            requestAnimationFrame(frame);
        }
    }

    function lerp(a, b, t) { return a + (b - a) * t; }
    function clamp01(x) { return Math.max(0, Math.min(1, x)); }
    function easeInOutSine(t) { return -(Math.cos(Math.PI * t) - 1) / 2; }

    // ------------------------------------------------------------------
    // 1) PROBLEMA Y CONTEXTO — bandas de calentamiento ("warming stripes")
    // que laten desde un nucleo, con particulas de CO2 subiendo. Referencia
    // directa a la propia metafora visual del proyecto.
    // ------------------------------------------------------------------
    function fondoProblema(ctx, w, h, t) {
        ctx.clearRect(0, 0, w, h);
        const cx = w * 0.82, cy = h * 0.62;
        const bandas = 7;
        for (let i = bandas; i >= 0; i--) {
            const fase = (t * 0.12 + i / bandas) % 1;
            const r = Math.max(0, fase * Math.max(w, h) * 0.95);
            const mezcla = i / bandas;
            const color = i % 2 === 0 ? PALETA.frio : PALETA.calido;
            ctx.beginPath();
            ctx.arc(cx, cy, r, 0, Math.PI * 2);
            ctx.strokeStyle = color;
            ctx.globalAlpha = (1 - fase) * 0.22;
            ctx.lineWidth = 14;
            ctx.stroke();
        }
        ctx.globalAlpha = 1;
        // Particulas de CO2 subiendo
        const n = 26;
        for (let i = 0; i < n; i++) {
            const semilla = i * 37.13;
            const x = (Math.sin(semilla) * 0.5 + 0.5) * w;
            const velocidad = 18 + (i % 5) * 6;
            const y = h - ((t * velocidad + semilla * 40) % (h + 40));
            const r = 1.4 + (i % 3);
            ctx.beginPath();
            ctx.arc(x, y, r, 0, Math.PI * 2);
            ctx.fillStyle = PALETA.blanco + (0.12 + 0.1 * Math.sin(t + i)) + ')';
            ctx.fill();
        }
    }

    // ------------------------------------------------------------------
    // 2) PREGUNTAS — El Nino vs La Nina "peleando" mientras el CO2 sube
    // fuerte y luego baja gradualmente. Controlado por el SCROLL de toda
    // la pagina (no por tiempo), via el progreso global calculado en
    // calcularProgresoScroll().
    // ------------------------------------------------------------------
    function fondoPreguntas(ctx, w, h, t, progreso) {
        ctx.clearRect(0, 0, w, h);
        ctx.fillStyle = '#05070f';
        ctx.fillRect(0, 0, w, h);

        // Envolvente asimetrica: sube rapido, baja gradual (nunca de golpe).
        const p = progreso == null ? 0 : progreso;
        let envolvente;
        if (p < 0.7) {
            envolvente = Math.pow(p / 0.7, 1.4);
        } else {
            envolvente = 1 - easeInOutSine((p - 0.7) / 0.3) * 0.55;
        }

        const pelea = Math.sin(t * 0.9) * 0.5 + 0.5; // quien domina ahora
        const ninoX = lerp(w * 0.28, w * 0.5, pelea) ;
        const ninaX = lerp(w * 0.72, w * 0.5, pelea);
        const radioBase = Math.min(w, h) * (0.22 + 0.1 * envolvente);

        function blob(x, y, r, color, alpha) {
            const grad = ctx.createRadialGradient(x, y, 0, x, y, r);
            grad.addColorStop(0, color);
            grad.addColorStop(1, 'transparent');
            ctx.globalAlpha = alpha;
            ctx.fillStyle = grad;
            ctx.beginPath();
            ctx.arc(x, y, r, 0, Math.PI * 2);
            ctx.fill();
        }
        blob(ninoX, h * 0.42, radioBase * (0.85 + 0.3 * pelea), PALETA.calido, 0.55);
        blob(ninaX, h * 0.58, radioBase * (1.15 - 0.3 * pelea), PALETA.frio, 0.5);

        // Haz de calor de CO2 creciendo con la envolvente
        ctx.globalAlpha = 0.18 + 0.4 * envolvente;
        const g = ctx.createLinearGradient(0, h, 0, 0);
        g.addColorStop(0, 'rgba(255,106,77,.55)');
        g.addColorStop(1, 'transparent');
        ctx.fillStyle = g;
        ctx.fillRect(0, h * (1 - envolvente * 0.6), w, h * envolvente * 0.6);

        // Particulas de CO2, cantidad segun la envolvente
        const nMax = 46;
        const n = Math.round(6 + nMax * envolvente);
        ctx.globalAlpha = 1;
        for (let i = 0; i < n; i++) {
            const semilla = i * 12.9;
            const x = ((Math.sin(semilla) * 0.5 + 0.5) * w + t * 6) % w;
            const y = h - ((t * (20 + (i % 6) * 5) + semilla * 50) % h);
            ctx.beginPath();
            ctx.arc(x, y, 1.6, 0, Math.PI * 2);
            ctx.fillStyle = 'rgba(255,180,84,' + (0.15 + 0.35 * envolvente) + ')';
            ctx.fill();
        }
    }

    function calcularProgresoScroll() {
        const doc = document.documentElement;
        const total = doc.scrollHeight - window.innerHeight;
        if (total <= 0) return 0;
        return clamp01(window.scrollY / total);
    }

    // ------------------------------------------------------------------
    // 3) NECESIDADES DE INFORMACION — red de nodos convergiendo a un
    // nodo central (la pregunta), con pulsos viajando por cada arista.
    // ------------------------------------------------------------------
    function fondoNecesidades(ctx, w, h, t) {
        ctx.clearRect(0, 0, w, h);
        const cx = w * 0.8, cy = h * 0.5;
        const etiquetas = ['Entidades', 'Variables', 'Periodo', 'Cobertura', 'Granularidad', 'Integracion'];
        const radio = Math.min(w, h) * 0.34;
        const nodos = etiquetas.map((txt, i) => {
            const ang = (i / etiquetas.length) * Math.PI * 2 + t * 0.05;
            return { x: cx + Math.cos(ang) * radio, y: cy + Math.sin(ang) * radio * 0.62, txt };
        });

        nodos.forEach((n) => {
            ctx.beginPath();
            ctx.moveTo(n.x, n.y);
            ctx.lineTo(cx, cy);
            ctx.strokeStyle = 'rgba(73,199,224,.18)';
            ctx.lineWidth = 1.4;
            ctx.stroke();

            const fase = (t * 0.35 + n.x * 0.01) % 1;
            const px = lerp(n.x, cx, fase);
            const py = lerp(n.y, cy, fase);
            ctx.beginPath();
            ctx.arc(px, py, 2.6, 0, Math.PI * 2);
            ctx.fillStyle = PALETA.ambar;
            ctx.fill();

            ctx.beginPath();
            ctx.arc(n.x, n.y, 5, 0, Math.PI * 2);
            ctx.fillStyle = 'rgba(255,255,255,.85)';
            ctx.fill();

            ctx.font = '11px "IBM Plex Mono", monospace';
            ctx.fillStyle = 'rgba(255,255,255,.55)';
            ctx.textAlign = n.x > cx ? 'left' : 'right';
            ctx.fillText(n.txt, n.x + (n.x > cx ? 9 : -9), n.y + 4);
        });

        ctx.beginPath();
        ctx.arc(cx, cy, 12 + Math.sin(t * 2) * 2, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(255,106,77,.85)';
        ctx.fill();
    }

    // ------------------------------------------------------------------
    // 4) FUENTES DE DATOS — mapa REAL (fuentes.jpg, ideal: NASA Black Marble
    // equirectangular, ver LISTA-DE-IMAGENES.md) con un pin en la posicion
    // geografica VERDADERA de cada institucion fuente, emitiendo un pulso
    // periodico ("notificacion" de dato entrante) hacia un punto de
    // consolidacion. Ya no se dibujan continentes esquematicos: la foto de
    // fondo (fondo-foto-fuentes, ver fondos.css) ya muestra el mundo real,
    // asi que este canvas solo pinta los pines/pulsos por ENCIMA de ella.
    //
    // Posiciones calculadas con proyeccion equirectangular a partir de
    // lat/lon reales (formula: x = (lon+180)/360, y = (90-lat)/180):
    //   OWID   -> Oxford, Reino Unido     (51.75 N, -1.25)
    //   IDEAM  -> Bogota, Colombia        (4.71 N, -74.07)
    //   NOAA   -> Silver Spring, EE.UU.   (38.99 N, -76.94)
    //   UNGRD  -> Bogota, Colombia        (3.50 N, -72.50 — desplazado un
    //             poco de IDEAM para que los dos pines no se encimen)
    //   UNFCCC -> Bonn, Alemania          (50.73 N, 7.10)
    // ------------------------------------------------------------------
    function fondoFuentes(ctx, w, h, t) {
        ctx.clearRect(0, 0, w, h);

        const centro = { x: w * 0.5, y: h * 0.85 };
        const fuentes = [
            { x: 0.4965, y: 0.2125, nombre: 'OWID' },
            { x: 0.2863, y: 0.2834, nombre: 'NOAA' },
            { x: 0.5197, y: 0.2182, nombre: 'UNFCCC' },
            { x: 0.2942, y: 0.4738, nombre: 'IDEAM' },
            { x: 0.2986, y: 0.4806, nombre: 'UNGRD' },
        ];
        fuentes.forEach((f, i) => {
            const x = f.x * w, y = f.y * h;
            ctx.beginPath();
            ctx.moveTo(x, y);
            ctx.lineTo(centro.x, centro.y);
            ctx.strokeStyle = 'rgba(61,220,151,.14)';
            ctx.lineWidth = 1;
            ctx.stroke();

            const fase = (t * 0.28 + i * 0.2) % 1;
            const px = lerp(x, centro.x, fase);
            const py = lerp(y, centro.y, fase);
            ctx.beginPath();
            ctx.arc(px, py, 2.4, 0, Math.PI * 2);
            ctx.fillStyle = PALETA.ok;
            ctx.fill();

            const pulso = 5 + Math.sin(t * 2.4 + i) * 1.5;
            ctx.beginPath();
            ctx.arc(x, y, pulso, 0, Math.PI * 2);
            ctx.strokeStyle = 'rgba(73,199,224,.5)';
            ctx.lineWidth = 1.4;
            ctx.stroke();
            ctx.beginPath();
            ctx.arc(x, y, 3, 0, Math.PI * 2);
            ctx.fillStyle = '#fff';
            ctx.fill();

            ctx.font = '10px "IBM Plex Mono", monospace';
            ctx.fillStyle = 'rgba(255,255,255,.6)';
            ctx.textAlign = 'center';
            ctx.fillText(f.nombre, x, y - pulso - 6);
        });

        ctx.beginPath();
        ctx.arc(centro.x, centro.y, 6, 0, Math.PI * 2);
        ctx.fillStyle = PALETA.calido;
        ctx.fill();
    }

    // ------------------------------------------------------------------
    // 5) DATASET — filas de celdas consolidandose desde los lados hacia
    // el centro, como si varias fuentes se unieran en una sola tabla.
    // ------------------------------------------------------------------
    function fondoDataset(ctx, w, h, t) {
        ctx.clearRect(0, 0, w, h);
        const filas = 8, cols = 10;
        const colores = [PALETA.frio, PALETA.calido, PALETA.ambar, PALETA.ok];
        const cellW = w / (cols + 4), cellH = h / (filas + 2);
        for (let r = 0; r < filas; r++) {
            const dir = r % 2 === 0 ? 1 : -1;
            const avance = (Math.sin(t * 0.6 + r * 0.4) * 0.5 + 0.5);
            for (let c = 0; c < cols; c++) {
                const objetivoX = (2 + c) * cellW;
                const inicioX = dir > 0 ? -cellW * 2 : w + cellW * 2;
                const x = lerp(inicioX, objetivoX, clamp01(avance * 1.3 - c * 0.02));
                const y = (1 + r) * cellH;
                const color = colores[(r + c) % colores.length];
                ctx.globalAlpha = 0.16 + 0.1 * Math.sin(t + r + c);
                ctx.fillStyle = color;
                ctx.fillRect(x, y, cellW * 0.72, cellH * 0.5);
            }
        }
        ctx.globalAlpha = 1;
    }

    // ------------------------------------------------------------------
    // 6) DICCIONARIO DE DATOS — nube de etiquetas (glosario) flotando.
    // ------------------------------------------------------------------
    function fondoDiccionario(ctx, w, h, t) {
        ctx.clearRect(0, 0, w, h);
        const terminos = [
            ['co2_per_capita', PALETA.frio], ['ghg_excluding_lucf', PALETA.calido],
            ['iso_code', PALETA.ok], ['year', PALETA.ambar], ['population', PALETA.morado],
            ['temperature_change', PALETA.calido], ['methane', PALETA.frio],
            ['nitrous_oxide', PALETA.ambar], ['nivel_geografico', PALETA.ok],
        ];
        terminos.forEach(([txt, color], i) => {
            const semilla = i * 91.7;
            const x = (Math.sin(semilla * 0.7 + t * 0.05) * 0.5 + 0.5) * w;
            const y = ((Math.cos(semilla * 0.9) * 0.5 + 0.5) * h + t * (6 + i * 1.3)) % h;
            ctx.globalAlpha = 0.28;
            ctx.beginPath();
            ctx.arc(x, y, 3, 0, Math.PI * 2);
            ctx.fillStyle = color;
            ctx.fill();
            ctx.font = '11px "IBM Plex Mono", monospace';
            ctx.fillStyle = color;
            ctx.globalAlpha = 0.22;
            ctx.textAlign = 'left';
            ctx.fillText(txt, x + 8, y + 4);
        });
        ctx.globalAlpha = 1;
    }

    // ------------------------------------------------------------------
    // 7) CALIDAD INICIAL — barrido de escaner sobre una grilla, revelando
    // huecos (valores nulos) al pasar.
    // ------------------------------------------------------------------
    function fondoCalidad(ctx, w, h, t) {
        ctx.clearRect(0, 0, w, h);
        const cols = 22, filas = 12;
        const cw = w / cols, ch = h / filas;
        const barridoX = (Math.sin(t * 0.5) * 0.5 + 0.5) * w;
        for (let r = 0; r < filas; r++) {
            for (let c = 0; c < cols; c++) {
                const x = c * cw, y = r * ch;
                const dist = Math.abs((x + cw / 2) - barridoX);
                const cerca = clamp01(1 - dist / (w * 0.08));
                const esFalla = ((r * 31 + c * 17) % 23) === 0;
                ctx.globalAlpha = 0.05 + cerca * 0.18;
                ctx.fillStyle = esFalla && cerca > 0.4 ? PALETA.calido : PALETA.frio;
                ctx.fillRect(x + 1, y + 1, cw - 2, ch - 2);
            }
        }
        ctx.globalAlpha = 0.55;
        ctx.fillStyle = 'rgba(255,255,255,.9)';
        ctx.fillRect(barridoX - 1, 0, 2, h);
        ctx.globalAlpha = 1;
    }

    // ------------------------------------------------------------------
    // 8) LIMITACIONES — niebla con grietas translucidas a la deriva.
    // ------------------------------------------------------------------
    function fondoLimitaciones(ctx, w, h, t) {
        ctx.clearRect(0, 0, w, h);
        const grietas = 5;
        for (let i = 0; i < grietas; i++) {
            const semilla = i * 53.1;
            const ox = (Math.sin(semilla) * 0.5 + 0.5) * w;
            const oy = (Math.cos(semilla * 1.3) * 0.5 + 0.5) * h;
            ctx.beginPath();
            ctx.moveTo(ox, oy);
            let x = ox, y = oy;
            for (let s = 0; s < 6; s++) {
                x += Math.sin(t * 0.1 + i + s) * 26;
                y += 22 + Math.cos(t * 0.08 + i + s) * 10;
                ctx.lineTo(x, y);
            }
            ctx.strokeStyle = 'rgba(255,180,84,' + (0.1 + 0.05 * Math.sin(t * 0.3 + i)) + ')';
            ctx.lineWidth = 1.2;
            ctx.stroke();
        }
        const niebla = ctx.createRadialGradient(w * 0.7, h * 0.4, 0, w * 0.7, h * 0.4, Math.max(w, h) * 0.6);
        niebla.addColorStop(0, 'rgba(255,255,255,.05)');
        niebla.addColorStop(1, 'transparent');
        ctx.fillStyle = niebla;
        ctx.fillRect(0, 0, w, h);
    }

    // ------------------------------------------------------------------
    // 9) RECOLECCION DE DATOS · Descripcion del conjunto — tres anillos
    // concentricos (Global / Regional / Nacional, los tres niveles reales
    // del dataset) donde van cayendo particulas que se asientan en el
    // anillo que les corresponde: la consolidacion multinivel que describe
    // esta pagina.
    // ------------------------------------------------------------------
    function fondoE2Descripcion(ctx, w, h, t) {
        ctx.clearRect(0, 0, w, h);
        const cx = w * 0.78, cy = h * 0.55;
        const radios = [0.44, 0.29, 0.15].map((f) => Math.min(w, h) * f);
        const colores = [PALETA.frio, PALETA.ambar, PALETA.calido];
        radios.forEach((r, i) => {
            ctx.beginPath();
            ctx.arc(cx, cy, r, 0, Math.PI * 2);
            ctx.strokeStyle = colores[i];
            ctx.globalAlpha = 0.22;
            ctx.lineWidth = 1.4;
            ctx.stroke();
        });
        ctx.globalAlpha = 1;
        const n = 30;
        for (let i = 0; i < n; i++) {
            const anillo = i % 3;
            const semilla = i * 17.3;
            const ang = semilla + t * (0.15 + anillo * 0.05);
            const r = radios[anillo] * (0.94 + 0.05 * Math.sin(t * 0.7 + i));
            const x = cx + Math.cos(ang) * r;
            const y = cy + Math.sin(ang) * r * 0.9;
            ctx.beginPath();
            ctx.arc(x, y, 2.2, 0, Math.PI * 2);
            ctx.fillStyle = colores[anillo];
            ctx.globalAlpha = 0.55;
            ctx.fill();
        }
        ctx.globalAlpha = 1;
        ctx.beginPath();
        ctx.arc(cx, cy, 4, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(255,255,255,.85)';
        ctx.fill();
    }

    // ------------------------------------------------------------------
    // 10) RECOLECCION DE DATOS · Perfilamiento — columnas verticales (una
    // por columna del dataset) con un barrido horizontal tipo "microscopio"
    // que revela la altura (cardinalidad/nulos) de cada una al pasar.
    // ------------------------------------------------------------------
    function fondoE2Perfilamiento(ctx, w, h, t) {
        ctx.clearRect(0, 0, w, h);
        const cols = 12;
        const cw = w / (cols + 2);
        const barridoX = ((t * 0.16) % 1.3 - 0.15) * w;
        for (let i = 0; i < cols; i++) {
            const x = (i + 1) * cw;
            const alturaBase = 0.2 + ((i * 53) % 100) / 130;
            const dist = Math.abs(x - barridoX);
            const cerca = clamp01(1 - dist / (w * 0.12));
            const altura = h * alturaBase * (0.85 + 0.15 * cerca);
            ctx.globalAlpha = 0.14 + cerca * 0.3;
            ctx.fillStyle = i % 3 === 0 ? PALETA.frio : (i % 3 === 1 ? PALETA.ambar : PALETA.morado);
            ctx.fillRect(x - cw * 0.28, h - altura, cw * 0.56, altura);
        }
        ctx.globalAlpha = 0.5;
        ctx.fillStyle = 'rgba(255,255,255,.85)';
        ctx.fillRect(barridoX - 1, 0, 2, h);
        ctx.globalAlpha = 1;
    }

    // ------------------------------------------------------------------
    // 11) RECOLECCION DE DATOS · Dimensiones y metricas — radar hexagonal
    // (las 6 dimensiones de calidad evaluadas) con el poligono de resultados
    // "respirando" cerca del borde, como el conjunto llega con alta calidad.
    // ------------------------------------------------------------------
    function fondoE2Dimensiones(ctx, w, h, t) {
        ctx.clearRect(0, 0, w, h);
        const cx = w * 0.8, cy = h * 0.52, r = Math.min(w, h) * 0.32;
        const ejes = 6;
        for (let anillo = 1; anillo <= 3; anillo++) {
            ctx.beginPath();
            for (let i = 0; i <= ejes; i++) {
                const ang = (i / ejes) * Math.PI * 2 - Math.PI / 2;
                const rr = r * (anillo / 3);
                const x = cx + Math.cos(ang) * rr, y = cy + Math.sin(ang) * rr * 0.92;
                i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
            }
            ctx.strokeStyle = 'rgba(255,255,255,.1)';
            ctx.lineWidth = 1;
            ctx.stroke();
        }
        ctx.beginPath();
        for (let i = 0; i <= ejes; i++) {
            const ang = (i / ejes) * Math.PI * 2 - Math.PI / 2;
            const rr = r * (0.86 + 0.08 * Math.sin(t * 1.1 + i));
            const x = cx + Math.cos(ang) * rr, y = cy + Math.sin(ang) * rr * 0.92;
            i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
            ctx.fillStyle = PALETA.ok;
            ctx.globalAlpha = 1;
            ctx.beginPath(); ctx.arc(x, y, 3, 0, Math.PI * 2); ctx.fill();
            ctx.beginPath();
            const ang2 = (i / ejes) * Math.PI * 2 - Math.PI / 2;
            const rr2 = r * (0.86 + 0.08 * Math.sin(t * 1.1 + i));
            ctx.moveTo(cx + Math.cos(ang2) * rr2, cy + Math.sin(ang2) * rr2 * 0.92);
        }
        ctx.closePath();
        ctx.fillStyle = 'rgba(61,220,151,.14)';
        ctx.fill();
        ctx.strokeStyle = PALETA.ok;
        ctx.globalAlpha = 0.7;
        ctx.lineWidth = 1.6;
        ctx.stroke();
        ctx.globalAlpha = 1;
    }

    // ------------------------------------------------------------------
    // 12) RECOLECCION DE DATOS · Problemas identificados — barrido tipo
    // radar/sonar que hace "sonar" los hallazgos del perfilamiento; el
    // tamano/brillo de cada blip sigue su severidad (alta = mas cerca).
    // ------------------------------------------------------------------
    function fondoE2Problemas(ctx, w, h, t) {
        ctx.clearRect(0, 0, w, h);
        const cx = w * 0.8, cy = h * 0.55, rMax = Math.min(w, h) * 0.46;
        for (let a = 1; a <= 3; a++) {
            ctx.beginPath();
            ctx.arc(cx, cy, rMax * a / 3, 0, Math.PI * 2);
            ctx.strokeStyle = 'rgba(255,180,84,.14)';
            ctx.lineWidth = 1;
            ctx.stroke();
        }
        const blips = [
            { ang: 0.4, rf: 0.35, sev: 1 }, { ang: 1.6, rf: 0.55, sev: 0.4 },
            { ang: 2.6, rf: 0.85, sev: 0.6 }, { ang: 3.5, rf: 0.62, sev: 0.6 },
            { ang: 4.4, rf: 0.9, sev: 0.3 }, { ang: 5.4, rf: 0.42, sev: 0.6 },
        ];
        const anguloBarrido = (t * 0.6) % (Math.PI * 2);
        ctx.save();
        ctx.beginPath();
        ctx.moveTo(cx, cy);
        ctx.arc(cx, cy, rMax, anguloBarrido - 0.5, anguloBarrido);
        ctx.closePath();
        ctx.fillStyle = 'rgba(255,180,84,.08)';
        ctx.fill();
        ctx.restore();
        blips.forEach((b) => {
            const x = cx + Math.cos(b.ang) * rMax * b.rf;
            const y = cy + Math.sin(b.ang) * rMax * b.rf * 0.9;
            let diff = Math.abs(((anguloBarrido - b.ang) + Math.PI * 3) % (Math.PI * 2) - Math.PI);
            const recienTocado = clamp01(1 - diff / 0.5);
            const radio = 2.5 + b.sev * 3 + recienTocado * 4;
            ctx.beginPath();
            ctx.arc(x, y, radio, 0, Math.PI * 2);
            ctx.fillStyle = PALETA.calido;
            ctx.globalAlpha = 0.35 + b.sev * 0.3 + recienTocado * 0.35;
            ctx.fill();
        });
        ctx.globalAlpha = 1;
    }

    // ------------------------------------------------------------------
    // 13) RECOLECCION DE DATOS · Tratamiento — linea de ensamblaje: los
    // puntos entran dispersos por la izquierda y salen alineados en una
    // grilla ordenada por la derecha, pasando por "estaciones" de limpieza.
    // ------------------------------------------------------------------
    function fondoE2Tratamiento(ctx, w, h, t) {
        ctx.clearRect(0, 0, w, h);
        const estaciones = 4;
        for (let i = 1; i <= estaciones; i++) {
            const x = (w * i) / (estaciones + 1);
            ctx.strokeStyle = 'rgba(73,199,224,.14)';
            ctx.lineWidth = 1;
            ctx.beginPath(); ctx.moveTo(x, h * 0.1); ctx.lineTo(x, h * 0.9); ctx.stroke();
        }
        const n = 24;
        for (let i = 0; i < n; i++) {
            const fase = ((t * 0.09) + i / n) % 1;
            const x = fase * w;
            const filaObjetivo = i % 6;
            const yObjetivo = h * (0.2 + filaObjetivo * 0.11);
            const yCaotico = h * (0.15 + ((i * 37) % 100) / 130);
            const orden = clamp01(fase * 1.15);
            const y = lerp(yCaotico, yObjetivo, orden);
            ctx.beginPath();
            ctx.arc(x, y, 2.4, 0, Math.PI * 2);
            ctx.fillStyle = orden > 0.7 ? PALETA.ok : PALETA.frio;
            ctx.globalAlpha = 0.5;
            ctx.fill();
        }
        ctx.globalAlpha = 1;
    }

    // ------------------------------------------------------------------
    // 14) RECOLECCION DE DATOS · Comparacion antes/despues — espejo: puntos
    // dispersos a la izquierda (antes) y los mismos, ordenados en una
    // grilla, a la derecha (despues), con la linea divisoria pulsando.
    // ------------------------------------------------------------------
    function fondoE2Comparacion(ctx, w, h, t) {
        ctx.clearRect(0, 0, w, h);
        const mid = w * 0.5;
        const n = 30;
        for (let i = 0; i < n; i++) {
            const semilla = i * 29.7;
            const xa = (Math.sin(semilla) * 0.5 + 0.5) * mid * 0.82;
            const ya = (Math.cos(semilla * 1.7) * 0.5 + 0.5) * h;
            const jitterA = Math.sin(t * 1.4 + i) * 4;
            ctx.beginPath();
            ctx.arc(xa + jitterA, ya, 2.2, 0, Math.PI * 2);
            ctx.fillStyle = PALETA.calido;
            ctx.globalAlpha = 0.4;
            ctx.fill();

            const cols = 6, filas = 5;
            const c = i % cols, r = Math.floor(i / cols) % filas;
            const xb = mid * 1.18 + (c + 0.5) * (mid * 0.7 / cols);
            const yb = (r + 0.5) * (h / filas);
            ctx.beginPath();
            ctx.arc(xb, yb, 2.2, 0, Math.PI * 2);
            ctx.fillStyle = PALETA.ok;
            ctx.globalAlpha = 0.55;
            ctx.fill();
        }
        ctx.globalAlpha = 0.15 + 0.1 * Math.sin(t * 2);
        ctx.fillStyle = 'rgba(255,255,255,.9)';
        ctx.fillRect(mid - 1, 0, 2, h);
        ctx.globalAlpha = 1;
    }

    // ------------------------------------------------------------------
    // 15) RECOLECCION DE DATOS · Graficas e indicadores — tablero de barras
    // horizontales animadas, eco directo de los graficos reales de la
    // pagina (por fuente, por indicador atipico).
    // ------------------------------------------------------------------
    function fondoE2Graficas(ctx, w, h, t) {
        ctx.clearRect(0, 0, w, h);
        const filas = 6;
        const alturaFila = h / (filas + 1);
        for (let i = 0; i < filas; i++) {
            const y = (i + 0.7) * alturaFila;
            const base = 0.25 + ((i * 41) % 100) / 160;
            const pulso = base + 0.12 * Math.sin(t * 0.8 + i * 1.3);
            const ancho = w * 0.62 * clamp01(pulso);
            ctx.globalAlpha = 0.5;
            ctx.fillStyle = i % 2 === 0 ? PALETA.frio : PALETA.ambar;
            ctx.fillRect(w * 0.3, y, ancho, alturaFila * 0.4);
            ctx.beginPath();
            ctx.arc(w * 0.3 + ancho, y + alturaFila * 0.2, 3, 0, Math.PI * 2);
            ctx.fillStyle = '#fff';
            ctx.globalAlpha = 0.7;
            ctx.fill();
        }
        ctx.globalAlpha = 1;
    }

    const FONDOS = {
        problema: fondoProblema,
        necesidades: fondoNecesidades,
        fuentes: fondoFuentes,
        dataset: fondoDataset,
        diccionario: fondoDiccionario,
        calidad: fondoCalidad,
        limitaciones: fondoLimitaciones,
        e2_descripcion: fondoE2Descripcion,
        e2_perfilamiento: fondoE2Perfilamiento,
        e2_dimensiones: fondoE2Dimensiones,
        e2_problemas: fondoE2Problemas,
        e2_tratamiento: fondoE2Tratamiento,
        e2_comparacion: fondoE2Comparacion,
        e2_graficas: fondoE2Graficas,
    };

    document.addEventListener('DOMContentLoaded', () => {
        document.querySelectorAll('.page-hero[data-fondo]').forEach((hero) => {
            const clave = hero.dataset.fondo;

            if (clave === 'preguntas') {
                // Cruce (crossfade) entre las dos fotos reales -- La Nina
                // (fondo-foto-preguntas-base) y El Nino (...-cruce) -- segun
                // el progreso de scroll de toda la pagina. Es un listener
                // aparte del motor de canvas para que la opacidad se
                // actualice de inmediato al hacer scroll, incluso si el
                // usuario tiene "reduced motion" activado (ahi el canvas de
                // particulas no anima, pero el cruce de fotos si sigue
                // funcionando porque es solo una transicion de opacidad).
                const cruce = hero.querySelector('.fondo-foto-preguntas-cruce');
                const actualizarCruce = () => {
                    if (cruce) cruce.style.opacity = String(calcularProgresoScroll());
                };
                actualizarCruce();
                window.addEventListener('scroll', actualizarCruce, { passive: true });
                window.addEventListener('resize', actualizarCruce);

                const canvas = hero.querySelector('.fondo-preguntas-fijo');
                if (!canvas) return;
                motor(canvas, (ctx, w, h, t) => fondoPreguntas(ctx, w, h, t, calcularProgresoScroll()), { fija: true });
                return;
            }

            const fn = FONDOS[clave];
            const canvas = hero.querySelector('.fondo-seccion');
            if (!fn || !canvas) return;
            motor(canvas, fn);
        });
    });
})();
