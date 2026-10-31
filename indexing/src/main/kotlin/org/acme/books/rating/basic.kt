package org.acme.books.rating

import com.fasterxml.jackson.module.kotlin.jacksonObjectMapper
import io.github.resilience4j.ratelimiter.RateLimiter
import io.github.resilience4j.ratelimiter.RateLimiterConfig
import io.github.resilience4j.ratelimiter.RateLimiterRegistry
import org.apache.http.HttpHost
import org.apache.http.client.config.RequestConfig
import org.apache.http.impl.client.HttpClients
import org.elasticsearch.action.index.IndexRequest
import org.elasticsearch.client.RequestOptions
import org.elasticsearch.client.RestClient
import org.elasticsearch.client.RestHighLevelClient
import org.elasticsearch.common.xcontent.XContentType
import org.slf4j.LoggerFactory
import java.security.MessageDigest
import java.time.Duration

private val logger = LoggerFactory.getLogger("basic")

class DecoratedGoodReadsClient(
    private val goodReadsClient: GoodReadsClient,
    private val rateLimiter: RateLimiter
) {
    fun search(query: String): List<GoodReadsBook> {
        return rateLimiter.executeCallable { goodReadsClient.search(query) }
    }
}

fun main() {

    val dropboxSourceConfig = DropboxSourceConfig(
        path = "/ebooks.mobi.new.en",
        accessKey = System.getenv("DROPBOX_ACCESS_KEY"),
        accessSecret = null,
        limit = Int.MAX_VALUE,
        pageSize = 500
    )

    val rateLimiterRegistry = RateLimiterRegistry.ofDefaults()
    val rateLimiter = rateLimiterRegistry
        .rateLimiter("goodreads") {
            RateLimiterConfig
                .custom()
                // Implement some kind of backpressure
                .timeoutDuration(Duration.ofHours(1))
                .limitForPeriod(3)
                .limitRefreshPeriod(Duration.ofSeconds(1))
                .build()
        }

    val requestConfig = RequestConfig.custom()
        .setConnectTimeout(5000) // Connection timeout in milliseconds
        .setSocketTimeout(5000)  // Socket timeout in milliseconds
        .build()

    val goodReadsClient = DecoratedGoodReadsClient(
        goodReadsClient = GoodReadsClient(HttpClients.custom().setDefaultRequestConfig(requestConfig).build()),
        rateLimiter = rateLimiter
    )

    val esSink = RestHighLevelClient(
        RestClient.builder(HttpHost("localhost", 9200, "http")).setRequestConfigCallback { builder -> builder.setSocketTimeout(1)}
    )
    val esIndex = "books"

    val mapper = jacksonObjectMapper()

    dropboxEntries(dropboxSourceConfig, buildDropboxClient(dropboxSourceConfig))
        .stream()
        .map { it.name.lowercase() }
        .filter { it.endsWith(".mobi") }
        .map { it.replace(".mobi", "") }
        .map { query ->
            try {
                val books = goodReadsClient.search(query)
                query to books
            } catch (e: Exception) {
                logger.error("Failed to search for $query", e)
                // TODO place in some error queue
                query to emptyList()
            }
        }
        .filter { (_, books) -> books.isNotEmpty() }
        .forEach { (query, books) ->
            val jsonString = mapper.writeValueAsString(books[0])
            logger.info("Storing ${books[0]} into ES")

            val bytes = MessageDigest.getInstance("SHA-256").digest(books[0].name!!.toByteArray())
            val id = bytes.joinToString("") { "%02x".format(it) }

            val request = IndexRequest(esIndex)
                .id(id)
                .source(jsonString, XContentType.JSON)
            esSink.index(request, RequestOptions.DEFAULT)
        }

    esSink.close()
}
