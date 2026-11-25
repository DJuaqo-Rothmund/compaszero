package com.compaszero.text

/**
 * Contador de sílabas para español.
 *
 * Cuenta núcleos vocálicos: los diptongos y triptongos (vocal débil i/u + otra vocal)
 * forman una sola sílaba; dos vocales fuertes juntas (a, e, o, o débiles acentuadas í/ú)
 * forman hiato y cuentan como dos. La "u" muda de que/qui/gue/gui no cuenta y la "h"
 * intercalada no rompe el diptongo.
 */
object Syllables {

    private const val STRONG = "aeoáéóíú"
    private const val WEAK = "iuüy"

    /** Sílabas de una línea completa (suma de cada palabra, sin sinalefa). */
    fun countLine(line: String): Int =
        words(line).sumOf { countWord(it) }

    fun words(line: String): List<String> =
        line.lowercase().split(Regex("[^\\p{L}]+")).filter { it.isNotEmpty() }

    fun countWord(raw: String): Int {
        val w = raw.lowercase().filter { it.isLetter() }
        if (w.isEmpty()) return 0
        var count = 0
        var prev: Char? = null // última vocal del núcleo actual, null si venimos de consonante
        var i = 0
        while (i < w.length) {
            val c = w[i]
            when {
                c == 'h' -> { /* no rompe el grupo vocálico */ }
                isSilentU(w, i) -> prev = null
                isVowel(w, i) -> {
                    val p = prev
                    if (p == null || (p in STRONG && c in STRONG)) count++
                    prev = c
                }
                else -> prev = null
            }
            i++
        }
        return maxOf(count, 1)
    }

    private fun isVowel(w: String, i: Int): Boolean {
        val c = w[i]
        if (c == 'y') {
            // "y" es vocal sola, al final de palabra o antes de consonante (rey, muy, y)
            val next = w.getOrNull(i + 1)
            return next == null || !(next in STRONG || next in WEAK)
        }
        return c in STRONG || c in WEAK
    }

    private fun isSilentU(w: String, i: Int): Boolean =
        w[i] == 'u' && i > 0 && (w[i - 1] == 'q' || w[i - 1] == 'g') &&
            w.getOrNull(i + 1)?.let { it == 'e' || it == 'i' || it == 'é' || it == 'í' } == true
}
