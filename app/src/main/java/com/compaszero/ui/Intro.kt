package com.compaszero.ui

import android.graphics.Paint
import android.graphics.Path
import android.graphics.PathMeasure
import androidx.compose.animation.core.*
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.drawIntoCanvas
import androidx.compose.ui.graphics.lerp
import androidx.compose.ui.graphics.nativeCanvas
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.graphics.vector.PathParser
import androidx.compose.ui.graphics.asAndroidPath
import kotlin.math.min

private fun parse(d: String): Path = PathParser().parsePathString(d).toPath().asAndroidPath()

/** Dibuja la fracción [t] (0..1) de todos los contornos de [path], como un trazo que avanza. */
private class Traced(val path: Path) {
    private val contours: List<Pair<PathMeasure, Float>>
    private val total: Float
    init {
        val list = mutableListOf<Pair<PathMeasure, Float>>()
        val pm = PathMeasure(path, false)
        do {
            val m = PathMeasure()
            val seg = Path(); pm.getSegment(0f, pm.length, seg, true)
            m.setPath(seg, false)
            list += m to pm.length
        } while (pm.nextContour())
        contours = list
        total = list.sumOf { it.second.toDouble() }.toFloat()
    }

    private val pos = FloatArray(2)

    /** Posición de la "boquilla" del spray cuando va por la fracción [t]. */
    fun tip(t: Float): FloatArray? {
        var left = t * total
        for ((m, len) in contours) {
            if (left <= len) { m.getPosTan(left, pos, null); return pos }
            left -= len
        }
        return null
    }

    fun partial(t: Float): Path {
        val out = Path()
        var left = t * total
        for ((m, len) in contours) {
            if (left <= 0f) break
            m.getSegment(0f, min(left, len), out, true)
            left -= len
        }
        return out
    }
}

private fun ease(x: Float) = FastOutSlowInEasing.transform(x.coerceIn(0f, 1f))
private fun window(t: Float, start: Float, dur: Float) = ((t - start) / dur).coerceIn(0f, 1f)

private const val TOTAL = 4.8f

/**
 * Intro: aparece el símbolo con la luz REC latiendo, se trazan las letras de "Compás Zero",
 * luego las dos líneas de abajo y finalmente el lema. Tocar la pantalla la salta.
 */
@Composable
fun IntroScreen(onFinished: () -> Unit) {
    val symbol = remember { parse(LogoPaths.SYMBOL) }
    val letters = remember { LogoPaths.letters.map { Traced(parse(it)) } }
    val dots = remember { LogoPaths.dots.map(::parse) }
    val lines = remember { LogoPaths.underlines.map { Traced(parse(it)) } }
    val tagline = remember { Path().apply { LogoPaths.tagline.forEach { addPath(parse(it)) } } }

    val clock = remember { Animatable(0f) }
    LaunchedEffect(Unit) {
        clock.animateTo(TOTAL, tween((TOTAL * 1000).toInt(), easing = LinearEasing))
        onFinished()
    }
    val pulse by rememberInfiniteTransition(label = "rec").animateFloat(
        0f, 1f, infiniteRepeatable(tween(800, easing = FastOutSlowInEasing), RepeatMode.Reverse), label = "rec",
    )

    val fill = remember { Paint(Paint.ANTI_ALIAS_FLAG).apply { style = Paint.Style.FILL } }
    val brush = remember { Paint(Paint.ANTI_ALIAS_FLAG).apply { style = Paint.Style.STROKE; strokeJoin = Paint.Join.ROUND; strokeCap = Paint.Cap.ROUND; color = android.graphics.Color.WHITE } }
    val mist = remember { Paint(Paint.ANTI_ALIAS_FLAG).apply { color = android.graphics.Color.WHITE; maskFilter = android.graphics.BlurMaskFilter(10f, android.graphics.BlurMaskFilter.Blur.NORMAL) } }
    val srcIn = remember { android.graphics.PorterDuffXfermode(android.graphics.PorterDuff.Mode.SRC_IN) }
    val rnd = remember { java.util.Random(7) }
    val glow = remember { Paint(Paint.ANTI_ALIAS_FLAG).apply { maskFilter = android.graphics.BlurMaskFilter(14f, android.graphics.BlurMaskFilter.Blur.NORMAL) } }

    Canvas(
        Modifier.fillMaxSize().background(Brand.Ink)
            .clickable(remember { MutableInteractionSource() }, indication = null, onClick = onFinished)
    ) {
        val t = clock.value
        logo { canvas ->
            val white = Brand.Chalk.toArgb()

            // 1. Símbolo
            val s = ease(window(t, 0f, 0.6f))
            canvas.save()
            canvas.scale(0.85f + 0.15f * s, 0.85f + 0.15f * s, LogoPaths.DOT_X, LogoPaths.DOT_Y)
            fill.color = white; fill.alpha = (255 * s).toInt()
            canvas.drawPath(symbol, fill)
            val rec = lerp(Brand.Rec, Brand.RecOff, pulse)
            glow.color = Brand.Rec.toArgb(); glow.alpha = (230 * (1 - pulse) * s).toInt()
            canvas.drawCircle(LogoPaths.DOT_X, LogoPaths.DOT_Y, LogoPaths.DOT_R * 1.4f, glow)
            fill.color = rec.toArgb(); fill.alpha = (255 * s).toInt()
            canvas.drawCircle(LogoPaths.DOT_X, LogoPaths.DOT_Y, LogoPaths.DOT_R, fill)
            canvas.restore()

            // 2. Grafiti pintado en vivo: una boquilla de spray recorre cada letra,
            //    descubre la pintura por donde pasa y deja neblina y gotitas alrededor.
            fun traced(item: Traced, start: Float, dur: Float) {
                val p = window(t, start, dur)
                if (p <= 0f) return
                if (p >= 1f) { fill.color = white; fill.alpha = 255; canvas.drawPath(item.path, fill); return }
                val e = ease(p)
                val layer = canvas.saveLayer(null, null)
                brush.strokeWidth = 18f
                canvas.drawPath(item.partial(e), brush)            // zona ya pintada
                fill.color = white; fill.alpha = 255
                fill.xfermode = srcIn
                canvas.drawPath(item.path, fill)                    // la letra solo aparece ahí
                fill.xfermode = null
                canvas.restoreToCount(layer)
                item.tip(e)?.let { (x, y) ->
                    mist.alpha = 90; canvas.drawCircle(x, y, 9f, mist)  // neblina del spray
                    repeat(6) {                                         // gotitas sueltas
                        val a = rnd.nextFloat() * 6.283f; val r = 4f + rnd.nextFloat() * 10f
                        fill.color = white; fill.alpha = 120 + rnd.nextInt(120)
                        canvas.drawCircle(x + r * kotlin.math.cos(a), y + r * kotlin.math.sin(a), 0.3f + rnd.nextFloat() * 0.7f, fill)
                    }
                }
            }
            letters.forEachIndexed { i, l -> traced(l, 0.7f + i * 0.3f, 0.55f) }

            // Salpicaduras de spray
            dots.forEachIndexed { i, d ->
                val p = window(t, 2.9f + i * 0.03f, 0.25f)
                if (p > 0f) {
                    val b = android.graphics.RectF(); d.computeBounds(b, true)
                    val k = if (p < 0.7f) p / 0.7f * 1.4f else 1.4f - (p - 0.7f) / 0.3f * 0.4f
                    canvas.save(); canvas.scale(k, k, b.centerX(), b.centerY())
                    fill.color = white; fill.alpha = (255 * min(1f, p * 2)).toInt()
                    canvas.drawPath(d, fill); canvas.restore()
                }
            }

            // 3. Las dos líneas de abajo
            traced(lines[0], 3.1f, 0.45f)
            traced(lines[1], 3.4f, 0.35f)

            // 4. Lema
            val g = ease(window(t, 3.8f, 0.5f))
            if (g > 0f) {
                canvas.save(); canvas.translate(0f, 6f * (1 - g))
                fill.color = white; fill.alpha = (255 * g).toInt()
                canvas.drawPath(tagline, fill); canvas.restore()
            }
        }
    }
}

/** Ajusta el sistema de coordenadas del logo (viewBox) al centro de la pantalla. */
private inline fun DrawScope.logo(block: (android.graphics.Canvas) -> Unit) {
    drawIntoCanvas { c ->
        val canvas = c.nativeCanvas
        val scale = min(size.width / LogoPaths.WIDTH, size.height / LogoPaths.HEIGHT) * 0.95f
        canvas.save()
        canvas.translate(
            (size.width - LogoPaths.WIDTH * scale) / 2f,
            (size.height - LogoPaths.HEIGHT * scale) / 2f,
        )
        canvas.scale(scale, scale)
        block(canvas)
        canvas.restore()
    }
}
