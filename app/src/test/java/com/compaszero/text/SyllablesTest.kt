package com.compaszero.text

import org.junit.Assert.assertEquals
import org.junit.Test

class SyllablesTest {
    private fun check(word: String, n: Int) = assertEquals(word, n, Syllables.countWord(word))

    @Test fun simples() {
        check("casa", 2); check("rap", 1); check("micrófono", 4); check("compás", 2)
    }

    @Test fun diptongos() {
        check("ciudad", 2); check("bueno", 2); check("aire", 2); check("cuidado", 3)
    }

    @Test fun hiatos() {
        check("poeta", 3); check("día", 2); check("país", 2); check("leer", 2); check("baúl", 2)
    }

    @Test fun uMudaYh() {
        check("que", 1); check("guitarra", 3); check("pingüino", 3); check("ahumado", 3)
    }

    @Test fun y() {
        check("rey", 1); check("muy", 1); check("yo", 1); check("ayer", 2); check("y", 1)
    }

    @Test fun linea() {
        assertEquals(11, Syllables.countLine("Antes del beat, nace la idea."))
    }
}
