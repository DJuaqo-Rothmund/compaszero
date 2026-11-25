package com.compaszero.data

import android.content.Context
import androidx.room.*
import kotlinx.coroutines.flow.Flow

@Entity
data class Song(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val title: String,
    val updatedAt: Long = System.currentTimeMillis(),
)

/** Una barra (verso). Si [songId] es null vive en el banco de ideas. */
@Entity(
    foreignKeys = [ForeignKey(
        entity = Song::class, parentColumns = ["id"], childColumns = ["songId"],
        onDelete = ForeignKey.CASCADE,
    )],
    indices = [Index("songId")],
)
data class Bar(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val songId: Long? = null,
    val section: String = "",
    val text: String,
    val createdAt: Long = System.currentTimeMillis(),
)

data class SongSummary(val id: Long, val title: String, val updatedAt: Long, val bars: Int)

@Dao
interface NotebookDao {
    @Query("SELECT s.id, s.title, s.updatedAt, COUNT(b.id) AS bars FROM Song s LEFT JOIN Bar b ON b.songId = s.id GROUP BY s.id ORDER BY s.updatedAt DESC")
    fun songs(): Flow<List<SongSummary>>

    @Query("SELECT * FROM Song WHERE id = :id")
    fun song(id: Long): Flow<Song?>

    @Query("SELECT * FROM Bar WHERE songId = :songId ORDER BY createdAt")
    fun bars(songId: Long): Flow<List<Bar>>

    @Query("SELECT * FROM Bar WHERE songId IS NULL ORDER BY createdAt DESC")
    fun ideas(): Flow<List<Bar>>

    @Insert suspend fun insert(song: Song): Long
    @Insert suspend fun insert(bar: Bar): Long
    @Update suspend fun update(song: Song)
    @Update suspend fun update(bar: Bar)
    @Delete suspend fun delete(song: Song)
    @Delete suspend fun delete(bar: Bar)

    @Query("UPDATE Song SET updatedAt = :now WHERE id = :id")
    suspend fun touch(id: Long, now: Long = System.currentTimeMillis())
}

@Database(entities = [Song::class, Bar::class], version = 1)
abstract class NotebookDb : RoomDatabase() {
    abstract fun dao(): NotebookDao

    companion object {
        @Volatile private var instance: NotebookDb? = null
        fun get(context: Context): NotebookDb = instance ?: synchronized(this) {
            instance ?: Room.databaseBuilder(context, NotebookDb::class.java, "cuaderno.db")
                .build().also { instance = it }
        }
    }
}
