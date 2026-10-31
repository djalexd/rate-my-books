package org.acme.books.rating

import com.dropbox.core.v2.DbxClientV2
import com.dropbox.core.v2.files.Metadata
import com.fasterxml.jackson.databind.ObjectMapper
import com.fasterxml.jackson.module.kotlin.registerKotlinModule
import org.apache.flink.api.common.functions.FilterFunction
import org.apache.flink.api.common.functions.FlatMapFunction
import org.apache.flink.api.common.typeinfo.TypeInformation
import org.apache.flink.api.java.typeutils.ResultTypeQueryable
import org.apache.flink.core.memory.DataInputView
import org.apache.flink.core.memory.DataOutputView
import org.apache.flink.streaming.api.functions.source.FromElementsFunction
import org.apache.flink.streaming.api.functions.source.SourceFunction
import org.apache.flink.streaming.api.environment.StreamExecutionEnvironment
import org.apache.flink.streaming.api.functions.sink.PrintSink
import org.apache.flink.types.Value
import org.apache.flink.util.Collector
import org.apache.http.impl.client.HttpClients
import java.util.function.Predicate

val objectMapper: ObjectMapper = ObjectMapper().registerKotlinModule()

/**
 * Wrap the types used in Flink Value for deser
 */
class MetadataValue(var metadata: Metadata? = null): Value {
    override fun write(to: DataOutputView) {
        val bytes = objectMapper.writeValueAsBytes(this)
        to.write(bytes)
    }

    override fun read(from: DataInputView) {
        val size = 16 * 1024
        val bytes = ByteArray(size)
        val read = from.read(bytes, 0, size)
        val valueRead = objectMapper.readValue(bytes, this.javaClass)
        // Mutation
        this.metadata = valueRead.metadata
    }
}

fun dropboxSource(config: DropboxSourceConfig, dbx: DbxClientV2): SourceFunction<MetadataValue> {
    val entries = dropboxEntries(config, dbx)
        .take(config.limit)
        .map { MetadataValue(it) }
    return FromElementsFunction(entries)
}

class GoodReadsBookValue(var book: GoodReadsBook? = null): Value {
    override fun write(to: DataOutputView) {
        val bytes = objectMapper.writeValueAsBytes(this)
        to.write(bytes)
    }

    override fun read(from: DataInputView) {
        val size = 16 * 1024
        val bytes = ByteArray(size)
        val read = from.read(bytes, 0, size)
        val valueRead = objectMapper.readValue(bytes, this.javaClass)
        // Mutation
        this.book = valueRead.book
    }
}

class ExtractBookMetadata(private val client: GoodReadsClient) : FlatMapFunction<MetadataValue, GoodReadsBookValue>, ResultTypeQueryable<GoodReadsBookValue> {
    override fun flatMap(value: MetadataValue, collector: Collector<GoodReadsBookValue>) {
        val query = value.metadata?.name?.replace(".mobi", "") ?: throw IllegalArgumentException("Invalid metadata: null")

        val books = client.search(query)
    }

    override fun getProducedType(): TypeInformation<GoodReadsBookValue> = TypeInformation.of(GoodReadsBookValue::class.java)
}

class FilterDropboxFiles(
    private val byPredicate: Predicate<Metadata?>
) : FilterFunction<MetadataValue>, ResultTypeQueryable<MetadataValue> {
    override fun filter(value: MetadataValue): Boolean {
        return byPredicate.test(value.metadata)
    }

    override fun getProducedType(): TypeInformation<MetadataValue> = TypeInformation.of(MetadataValue::class.java)
}

fun main() {
    val environment = StreamExecutionEnvironment()
    environment.parallelism = 1

    val dropboxSourceConfig = DropboxSourceConfig(
        path = "/books",
        accessKey = System.getenv("DROPBOX_ACCESS_KEY"),
        accessSecret = null,
        limit = 10,
        pageSize = 10
    )

    val goodreadsClient = GoodReadsClient(HttpClients.createDefault())

    environment
        .addSource(dropboxSource(dropboxSourceConfig, buildDropboxClient(dropboxSourceConfig)))
        .returns(TypeInformation.of(MetadataValue::class.java))

        .filter(FilterDropboxFiles { it?.name?.endsWith(".mobi") ?: false })
        .returns(TypeInformation.of(MetadataValue::class.java))

        .flatMap(ExtractBookMetadata(goodreadsClient))
        .returns(TypeInformation.of(GoodReadsBookValue::class.java))

        .sinkTo(PrintSink())
//        .sinkTo(Elasticsearch7SinkBuilder<GoodReadsBook>().build())

    environment.execute("ingest books")
}
