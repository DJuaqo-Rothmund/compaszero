package com.compaszero

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.BackHandler
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.animation.Crossfade
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.lifecycle.viewmodel.compose.viewModel
import com.compaszero.ui.*

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            CompasZeroTheme {
                var intro by rememberSaveable { mutableStateOf(true) }
                var songId by rememberSaveable { mutableStateOf<Long?>(null) }
                val vm: NotebookViewModel = viewModel()

                Crossfade(intro, label = "intro") { showIntro ->
                    if (showIntro) IntroScreen { intro = false }
                    else {
                        val open = songId
                        if (open == null) HomeScreen(vm) { songId = it }
                        else {
                            BackHandler { songId = null }
                            SongScreen(vm, open) { songId = null }
                        }
                    }
                }
            }
        }
    }
}
