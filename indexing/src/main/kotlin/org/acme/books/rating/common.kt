package org.acme.books.rating

import com.dropbox.core.DbxRequestConfig
import com.dropbox.core.v2.DbxClientV2
import com.dropbox.core.v2.files.Metadata
import org.apache.hc.core5.net.URIBuilder
import org.apache.http.client.HttpClient
import org.apache.http.client.methods.HttpGet
import org.apache.http.util.EntityUtils
import org.jsoup.Jsoup
import org.slf4j.LoggerFactory
import java.util.regex.Pattern

private val logger = LoggerFactory.getLogger("common")

data class DropboxSourceConfig(
    val path: String,
    val limit: Int = Int.MAX_VALUE,
    val pageSize: Int = 500,
    val cursor: String? = null,
    val accessKey: String,
    val accessSecret: ByteArray? = null
)

fun dropboxEntries(config: DropboxSourceConfig, dbx: DbxClientV2): List<Metadata> {
    val result = when (config.cursor != null) {
        true -> dbx.files().listFolderContinue(config.cursor)
        else -> dbx.files().listFolderBuilder(config.path).withRecursive(false).withLimit(config.pageSize.toLong()).start()
    }
    logger.info("Found ${result.entries.size} entries in ${config.path}")
    return result.entries + if (result.cursor != null && result.entries.isNotEmpty() && result.entries.size < config.limit) {
        dropboxEntries(config.copy(cursor = result.cursor), dbx)
    } else {
        emptyList()
    }
}

fun buildDropboxClient(config: DropboxSourceConfig): DbxClientV2 {
    val requestConfig = DbxRequestConfig
        .newBuilder("dropbox/java-tutorial")
        .build()
    return DbxClientV2(
        requestConfig,
        config.accessKey,
//        config.accessSecret?.toString()
    )
}

data class GoodReadsBook(
    val link: String,
    val name: String? = null,
    val rating: Float? = null,
    val author: String? = null,
    val ratingCount: Int? = null,
    val reviewsCount: Int? = null,
    val genres: List<String> = emptyList(),
    val language: String? = null
)

class GoodReadsClient(private val httpClient: HttpClient) {
    fun search(query: String): List<GoodReadsBook> {
        return try {
            val uri = URIBuilder("https://www.goodreads.com/search")
                .addParameter("q", query)
                .build()
            val request = HttpGet(uri)
                .apply {
                    addHeader("Accept", "text/html")
                    addHeader("Accept-Encoding", "gzip, deflate")
                    addHeader("User-Agent", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
                }
            // TODO timeout configured in HttpClient

            val response = httpClient.execute(request)
            val contentAsString = EntityUtils.toString(response.entity)

            val soup = Jsoup.parse(contentAsString)
            val bookTitles = soup.select("a.bookTitle")
            if (bookTitles.isEmpty()) return emptyList()
            val ratings = soup.select("span.minirating")
            val authors = soup.select("a.authorName")
            var books = bookTitles
                .mapIndexed { i, bookTitle ->
                    GoodReadsBook(
                        link = bookTitle.attr("href"),
                        name = bookTitle.text().lowercase(),
                        author = authors[i].text().lowercase(),
                        rating = extractRatingAndCount(ratings[i].text()).first,
                        ratingCount = extractRatingAndCount(ratings[i].text()).second,
                        reviewsCount = 0,
                        genres = emptyList(),
                        language = null
                    )
                }
                .sortedByDescending { it.ratingCount }
                .toMutableList()
            books = books.take(1).toMutableList()
            books.map { extractDetails(it) }
        } catch (e: Exception) {
            logger.error("Error fetching data from Goodreads: $e")
            emptyList()
        }
    }

    private fun extractRatingAndCount(text: String): Pair<Float, Int> {
        val pattern = Pattern.compile("(\\d+\\.\\d+)\\s+avg rating\\s+—\\s+([\\d,]+)\\s+ratings")
        val matcher = pattern.matcher(text)
        return if (matcher.find()) {
            val averageRating = matcher.group(1).toFloat()
            val ratingsCount = matcher.group(2).replace(",", "").toInt()
            averageRating to ratingsCount
        } else {
            0.0f to 0
        }
    }

    private fun extractReviewCount(text: String): Int {
        val pattern = Pattern.compile("(\\d+)\\s+reviews?")
        val matcher = pattern.matcher(text)
        return if (matcher.find()) {
            matcher.group(1).toInt()
        } else {
            0
        }
    }

    private fun extractDetails(book: GoodReadsBook): GoodReadsBook {
        return try {
            val uri = URIBuilder("https://www.goodreads.com${book.link}")
                .build()
            val request = HttpGet(uri)
                .apply {
                    addHeader("Accept", "text/html")
                    addHeader("Accept-Encoding", "gzip, deflate")
                    addHeader("User-Agent", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
                }

            val response = httpClient.execute(request)
            val soup = Jsoup.parse(EntityUtils.toString(response.entity))

            val genres = soup
                .select("span.BookPageMetadataSection__genreButton")
                .map { it.text().lowercase() }
            val reviewsCountText = soup
                .selectFirst("span[data-testid='reviewsCount']")
            val reviewsCount = reviewsCountText?.let { extractReviewCount(it.text()) } ?: 0

            book.copy(genres = genres, reviewsCount = reviewsCount)
        } catch (e: Exception) {
            logger.error("Error fetching data from goodreads", e)
            book
        }
    }
}
