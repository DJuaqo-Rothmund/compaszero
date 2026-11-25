package com.compaszero.ui

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.compaszero.data.Bar
import com.compaszero.data.NotebookDb
import com.compaszero.data.Song
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

class NotebookViewModel(app: Application) : AndroidViewModel(app) {
    private val dao = NotebookDb.get(app).dao()

    val songs = dao.songs().stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())
    val ideas = dao.ideas().stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    fun song(id: Long) = dao.song(id)
    fun bars(songId: Long) = dao.bars(songId)

    fun createSong(title: String, onCreated: (Long) -> Unit) = viewModelScope.launch {
        onCreated(dao.insert(Song(title = title.ifBlank { "Sin título" })))
    }

    fun renameSong(song: Song, title: String) = viewModelScope.launch {
        dao.update(song.copy(title = title, updatedAt = System.currentTimeMillis()))
    }

    fun deleteSong(song: Song) = viewModelScope.launch { dao.delete(song) }

    fun addBar(text: String, songId: Long? = null, section: String = "") = viewModelScope.launch {
        if (text.isBlank()) return@launch
        dao.insert(Bar(songId = songId, section = section, text = text.trim()))
        songId?.let { dao.touch(it) }
    }

    fun updateBar(bar: Bar) = viewModelScope.launch {
        dao.update(bar); bar.songId?.let { dao.touch(it) }
    }

    fun deleteBar(bar: Bar) = viewModelScope.launch { dao.delete(bar) }

    /** Mueve una idea suelta a una canción. */
    fun moveIdea(bar: Bar, songId: Long, section: String) = updateBar(
        bar.copy(songId = songId, section = section, createdAt = System.currentTimeMillis())
    )
}
