plugins {
    kotlin("jvm") version "2.0.0"
}

dependencies {
    implementation("org.apache.flink:flink-streaming-java:1.20.0")
    implementation("org.apache.flink:flink-clients:1.20.0")
    implementation("org.apache.flink:flink-connector-filesystem_2.12:1.11.6")
    implementation("org.apache.flink:flink-connector-elasticsearch7:1.16.3")

    implementation("com.dropbox.core:dropbox-core-sdk:5.4.0")
    implementation("org.slf4j:slf4j-api:1.7.32")
    implementation("org.slf4j:slf4j-log4j12:1.7.32")
    implementation("org.slf4j:jul-to-slf4j:1.7.32")
    implementation("org.slf4j:jcl-over-slf4j:1.7.32")
    implementation("org.slf4j:log4j-over-slf4j:1.7.32")

    implementation("ch.qos.logback:logback-classic:1.5.7")
    implementation("com.fasterxml.jackson.module:jackson-module-kotlin:2.13.0")
    implementation("org.apache.kafka:kafka-clients:3.0.0")
//    implementation("org.apache.flink:flink-connector-kafka_2.12:1.15.2")
    implementation("io.github.resilience4j:resilience4j-core:1.7.1")
    implementation("io.github.resilience4j:resilience4j-kotlin:1.7.1")
    implementation("io.github.resilience4j:resilience4j-ratelimiter:1.7.1")
    implementation("org.apache.httpcomponents.client5:httpclient5:5.1")
    implementation("org.jsoup:jsoup:1.14.3")
    testImplementation(kotlin("test"))
}
