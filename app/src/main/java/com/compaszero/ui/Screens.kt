package com.compaszero.ui

import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.background
import androidx.compose.foundation.combinedClickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.compaszero.data.Bar
import com.compaszero.data.Song
import com.compaszero.text.Syllables

val Sections = listOf("Intro", "Verso", "Coro", "Puente", "Outro")
private val Lyrics = FontFamily.Monospace

// ---------- Inicio: canciones + ideas ----------

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun HomeScreen(vm: NotebookViewModel, openSong: (Long) -> Unit) {
    var tab by rememberSaveable { mutableIntStateOf(0) }
    var newSong by remember { mutableStateOf(false) }

    Scaffold(
        topBar = {
            Column {
                CenterAlignedTopAppBar(title = { BrandTitle() })
                TabRow(selectedTabIndex = tab, containerColor = Brand.Ink) {
                    Tab(tab == 0, { tab = 0 }, text = { Text("Canciones") })
                    Tab(tab == 1, { tab = 1 }, text = { Text("Ideas sueltas") })
                }
            }
        },
        floatingActionButton = {
            if (tab == 0) FloatingActionButton(onClick = { newSong = true }, containerColor = Brand.Rec) {
                Icon(Icons.Default.Add, "Nueva canción")
            }
        },
    ) { pad ->
        Box(Modifier.padding(pad).fillMaxSize()) {
            if (tab == 0) SongList(vm, openSong) else IdeasTab(vm)
        }
    }

    if (newSong) TextDialog("Nueva canción", "Título", "", onDismiss = { newSong = false }) {
        newSong = false; vm.createSong(it, openSong)
    }
}

@Composable
private fun BrandTitle() = Row(verticalAlignment = Alignment.CenterVertically) {
    Text("Compás", fontWeight = FontWeight.Black)
    Box(Modifier.padding(horizontal = 6.dp).size(8.dp).clip(CircleShape).background(Brand.Rec))
    Text("Zero", fontWeight = FontWeight.Black)
}

@Composable
private fun SongList(vm: NotebookViewModel, openSong: (Long) -> Unit) {
    val songs by vm.songs.collectAsState()
    if (songs.isEmpty()) return Empty("Tu primera canción empieza aquí.\nToca + para crearla.")
    LazyColumn(contentPadding = PaddingValues(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
        items(songs, key = { it.id }) { s ->
            Card(
                onClick = { openSong(s.id) },
                colors = CardDefaults.cardColors(containerColor = Brand.Graphite),
                modifier = Modifier.fillMaxWidth(),
            ) {
                Column(Modifier.padding(16.dp)) {
                    Text(s.title, style = MaterialTheme.typography.titleMedium)
                    Text("${s.bars} barras", color = Brand.Muted, style = MaterialTheme.typography.bodySmall)
                }
            }
        }
    }
}

@OptIn(ExperimentalFoundationApi::class)
@Composable
private fun IdeasTab(vm: NotebookViewModel) {
    val ideas by vm.ideas.collectAsState()
    val songs by vm.songs.collectAsState()
    var selected by remember { mutableStateOf<Bar?>(null) }

    Column(Modifier.fillMaxSize()) {
        Box(Modifier.weight(1f)) {
            if (ideas.isEmpty()) Empty("Anota frases sueltas aquí.\nLuego muévelas a una canción.")
            else LazyColumn(contentPadding = PaddingValues(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                items(ideas, key = { it.id }) { bar ->
                    BarRow(bar, Modifier.combinedClickable(onClick = { selected = bar }, onLongClick = { selected = bar }))
                }
            }
        }
        Composer(placeholder = "Escribe una barra…") { vm.addBar(it) }
    }

    selected?.let { bar ->
        IdeaActions(bar, songs.map { it.id to it.title },
            onDismiss = { selected = null },
            onSave = { vm.updateBar(bar.copy(text = it)); selected = null },
            onMove = { id, section -> vm.moveIdea(bar, id, section); selected = null },
            onDelete = { vm.deleteBar(bar); selected = null })
    }
}

@Composable
private fun IdeaActions(
    bar: Bar, songs: List<Pair<Long, String>>,
    onDismiss: () -> Unit, onSave: (String) -> Unit,
    onMove: (Long, String) -> Unit, onDelete: () -> Unit,
) {
    var text by remember { mutableStateOf(bar.text) }
    var section by remember { mutableStateOf(Sections[1]) }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Idea") },
        text = {
            Column {
                LyricField(text, { text = it })
                if (songs.isNotEmpty()) {
                    Spacer(Modifier.height(12.dp))
                    Text("Mover a canción", color = Brand.Muted)
                    SectionChips(section) { section = it }
                    songs.forEach { (id, title) ->
                        TextButton(onClick = { onMove(id, section) }) { Text("→ $title") }
                    }
                }
            }
        },
        confirmButton = { TextButton(onClick = { onSave(text) }) { Text("Guardar") } },
        dismissButton = { TextButton(onClick = onDelete) { Text("Borrar", color = Brand.Rec) } },
    )
}

// ---------- Canción ----------

@OptIn(ExperimentalMaterial3Api::class, ExperimentalFoundationApi::class)
@Composable
fun SongScreen(vm: NotebookViewModel, songId: Long, onBack: () -> Unit) {
    val song by vm.song(songId).collectAsState(null)
    val bars by vm.bars(songId).collectAsState(emptyList())
    var section by rememberSaveable { mutableStateOf(Sections[1]) }
    var editing by remember { mutableStateOf<Bar?>(null) }
    var rename by remember { mutableStateOf(false) }
    var confirmDelete by remember { mutableStateOf(false) }

    Scaffold(topBar = {
        TopAppBar(
            title = { Text(song?.title ?: "", Modifier.combinedClickable(onClick = { rename = true })) },
            navigationIcon = { IconButton(onClick = onBack) { Icon(Icons.AutoMirrored.Filled.ArrowBack, "Volver") } },
            actions = { IconButton(onClick = { confirmDelete = true }) { Icon(Icons.Default.Delete, "Borrar canción") } },
        )
    }) { pad ->
        Column(Modifier.padding(pad).fillMaxSize()) {
            LazyColumn(Modifier.weight(1f), contentPadding = PaddingValues(16.dp)) {
                val grouped = bars.groupBy { it.section.ifBlank { "Sin sección" } }
                val order = Sections + grouped.keys.filter { it !in Sections }
                order.filter { it in grouped }.forEach { name ->
                    item(key = "h-$name") {
                        Text(name.uppercase(), color = Brand.Rec, fontWeight = FontWeight.Bold,
                            letterSpacing = 2.sp, modifier = Modifier.padding(top = 16.dp, bottom = 6.dp))
                    }
                    items(grouped.getValue(name), key = { it.id }) { bar ->
                        BarRow(bar, Modifier.combinedClickable(onClick = { editing = bar }, onLongClick = { editing = bar }))
                    }
                }
                if (bars.isEmpty()) item { Empty("Escribe la primera barra abajo.") }
            }
            SectionChips(section, Modifier.padding(horizontal = 12.dp)) { section = it }
            Composer(placeholder = "Barra en $section…") { vm.addBar(it, songId, section) }
        }
    }

    editing?.let { bar ->
        TextDialog("Editar barra", "Barra", bar.text, lyric = true,
            onDismiss = { editing = null },
            onDelete = { vm.deleteBar(bar); editing = null }) {
            vm.updateBar(bar.copy(text = it)); editing = null
        }
    }
    if (rename) song?.let { s ->
        TextDialog("Título", "Título", s.title, onDismiss = { rename = false }) { vm.renameSong(s, it); rename = false }
    }
    if (confirmDelete) song?.let { s ->
        AlertDialog(
            onDismissRequest = { confirmDelete = false },
            title = { Text("¿Borrar \"${s.title}\"?") },
            text = { Text("Se borran también sus barras.") },
            confirmButton = { TextButton(onClick = { vm.deleteSong(s); onBack() }) { Text("Borrar", color = Brand.Rec) } },
            dismissButton = { TextButton(onClick = { confirmDelete = false }) { Text("Cancelar") } },
        )
    }
}

// ---------- Piezas comunes ----------

@Composable
fun BarRow(bar: Bar, modifier: Modifier = Modifier) {
    Row(
        modifier.fillMaxWidth().clip(RoundedCornerShape(8.dp)).background(Brand.Graphite).padding(12.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text(bar.text, fontFamily = Lyrics, modifier = Modifier.weight(1f))
        SyllableBadge(Syllables.countLine(bar.text))
    }
    Spacer(Modifier.height(6.dp))
}

@Composable
private fun SyllableBadge(n: Int) {
    Text(
        "$n", fontFamily = Lyrics, color = Brand.Muted, fontSize = 12.sp,
        modifier = Modifier.padding(start = 8.dp).clip(CircleShape).background(Brand.Graphite2)
            .padding(horizontal = 8.dp, vertical = 2.dp),
    )
}

/** Barra de escritura rápida: Enter o el botón guardan y dejan el campo listo para la siguiente. */
@Composable
fun Composer(placeholder: String, onSubmit: (String) -> Unit) {
    var text by rememberSaveable { mutableStateOf("") }
    val submit = { if (text.isNotBlank()) { onSubmit(text); text = "" } }
    Row(
        Modifier.fillMaxWidth().background(Brand.Graphite).navigationBarsPadding().imePadding().padding(8.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        OutlinedTextField(
            text, { text = it }, Modifier.weight(1f),
            placeholder = { Text(placeholder) },
            textStyle = LocalTextStyle.current.copy(fontFamily = Lyrics),
            supportingText = { if (text.isNotBlank()) Text("${Syllables.countLine(text)} sílabas") },
            singleLine = true,
            keyboardActions = androidx.compose.foundation.text.KeyboardActions(onDone = { submit() }),
            keyboardOptions = androidx.compose.foundation.text.KeyboardOptions(
                imeAction = androidx.compose.ui.text.input.ImeAction.Done,
                capitalization = androidx.compose.ui.text.input.KeyboardCapitalization.Sentences,
            ),
        )
        IconButton(onClick = submit) { Icon(Icons.AutoMirrored.Filled.Send, "Guardar barra", tint = Brand.Rec) }
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun SectionChips(selected: String, modifier: Modifier = Modifier, onSelect: (String) -> Unit) {
    FlowRow(modifier, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
        Sections.forEach { s ->
            FilterChip(selected == s, { onSelect(s) }, label = { Text(s) },
                colors = FilterChipDefaults.filterChipColors(selectedContainerColor = Brand.Rec))
        }
    }
}

@Composable
private fun LyricField(value: String, onChange: (String) -> Unit) = OutlinedTextField(
    value, onChange, Modifier.fillMaxWidth(),
    textStyle = LocalTextStyle.current.copy(fontFamily = Lyrics),
    supportingText = { Text("${Syllables.countLine(value)} sílabas") },
)

@Composable
private fun TextDialog(
    title: String, label: String, initial: String, lyric: Boolean = false,
    onDismiss: () -> Unit, onDelete: (() -> Unit)? = null, onConfirm: (String) -> Unit,
) {
    var text by remember { mutableStateOf(initial) }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(title) },
        text = {
            if (lyric) LyricField(text) { text = it }
            else OutlinedTextField(text, { text = it }, label = { Text(label) }, singleLine = true)
        },
        confirmButton = { TextButton(onClick = { onConfirm(text) }) { Text("Guardar") } },
        dismissButton = {
            if (onDelete != null) TextButton(onClick = onDelete) { Text("Borrar", color = Brand.Rec) }
            else TextButton(onClick = onDismiss) { Text("Cancelar") }
        },
    )
}

@Composable
private fun Empty(text: String) = Box(Modifier.fillMaxSize().padding(32.dp), contentAlignment = Alignment.Center) {
    Text(text, color = Brand.Muted, textAlign = androidx.compose.ui.text.style.TextAlign.Center)
}
