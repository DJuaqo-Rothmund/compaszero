package com.compaszero.ui

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

object Brand {
    val Ink = Color(0xFF000000)
    val Chalk = Color(0xFFF5F5F5)
    val Rec = Color(0xFFE5194B)
    val RecOff = Color(0xFF3D0712)
    val Graphite = Color(0xFF1A1A1A)
    val Graphite2 = Color(0xFF2A2A2A)
    val Muted = Color(0xFF8A8A8A)
}

@Composable
fun CompasZeroTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = darkColorScheme(
            primary = Brand.Rec,
            onPrimary = Brand.Chalk,
            secondary = Brand.Chalk,
            background = Brand.Ink,
            onBackground = Brand.Chalk,
            surface = Brand.Ink,
            onSurface = Brand.Chalk,
            surfaceVariant = Brand.Graphite,
            onSurfaceVariant = Brand.Muted,
            surfaceContainer = Brand.Graphite,
            surfaceContainerHigh = Brand.Graphite2,
            outline = Brand.Graphite2,
        ),
        content = content,
    )
}
