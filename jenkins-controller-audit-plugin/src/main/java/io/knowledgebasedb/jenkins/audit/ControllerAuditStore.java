package io.knowledgebasedb.jenkins.audit;

import edu.umd.cs.findbugs.annotations.NonNull;
import hudson.model.Run;
import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.channels.FileChannel;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.security.MessageDigest;
import java.util.HexFormat;
import java.util.concurrent.atomic.AtomicBoolean;
import net.sf.json.JSONObject;

final class ControllerAuditStore {
    static final String DIRECTORY_PROPERTY = "knowledgebasedb.controllerAuditDir";
    private static final AtomicBoolean WRITE_HEALTHY = new AtomicBoolean(true);

    private ControllerAuditStore() {}

    static Path directory() { return Path.of(System.getProperty(DIRECTORY_PROPERTY, "")); }
    static boolean writable() {
        Path root = directory();
        return WRITE_HEALTHY.get() && !root.toString().isBlank() && Files.isDirectory(root)
            && Files.isWritable(root) && Files.isRegularFile(root.resolve(".healthy"));
    }
    static boolean healthy() { return writable() && !Files.exists(directory().resolve(".recovery-block")); }
    static String fileKey(String buildId) {
        try { return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(buildId.getBytes(StandardCharsets.UTF_8))); }
        catch (Exception exception) { throw new IllegalStateException(exception); }
    }
    static void persistBoth(@NonNull Run<?, ?> run, @NonNull JSONObject event) throws IOException {
        run.save();
        Path buildXml = run.getRootDir().toPath().resolve("build.xml");
        try (FileChannel normal = FileChannel.open(buildXml, StandardOpenOption.WRITE)) { normal.force(true); }
        append(event);
    }
    static void append(@NonNull JSONObject event) throws IOException {
        if (!writable()) throw new IOException("replicated controller-audit store is unhealthy");
        Path path = directory().resolve(fileKey(event.getString("buildId")) + ".jsonl");
        byte[] bytes = (event.toString() + "\n").getBytes(StandardCharsets.UTF_8);
        try (FileChannel channel = FileChannel.open(path, StandardOpenOption.CREATE, StandardOpenOption.WRITE, StandardOpenOption.APPEND)) {
            try (var ignored = channel.lock()) { channel.write(ByteBuffer.wrap(bytes)); channel.force(true); }
        } catch (IOException exception) { WRITE_HEALTHY.set(false); throw exception; }
    }
    static void blockRecovery(String buildId) throws IOException {
        Path markers = directory().resolve("recovery-blocks"); Files.createDirectories(markers);
        forceWrite(markers.resolve(fileKey(buildId)), buildId + "\n");
        forceWrite(directory().resolve(".recovery-block"), "post-mutation orphan recovery required\n");
    }
    static void releaseRecovery(String buildId) throws IOException {
        Path markers = directory().resolve("recovery-blocks"); Files.deleteIfExists(markers.resolve(fileKey(buildId)));
        try (var remaining = Files.isDirectory(markers) ? Files.list(markers) : java.util.stream.Stream.<Path>empty()) {
            if (remaining.findAny().isEmpty()) Files.deleteIfExists(directory().resolve(".recovery-block"));
        }
    }
    private static void forceWrite(Path path, String value) throws IOException {
        try (FileChannel channel = FileChannel.open(path, StandardOpenOption.CREATE, StandardOpenOption.TRUNCATE_EXISTING, StandardOpenOption.WRITE)) {
            channel.write(ByteBuffer.wrap(value.getBytes(StandardCharsets.UTF_8))); channel.force(true);
        }
    }
    static void retentionCleanup() throws IOException {
        long cutoff = System.currentTimeMillis() - 90L * 24 * 60 * 60 * 1000;
        try (var paths = Files.list(directory())) {
            paths.filter(path -> path.getFileName().toString().endsWith(".jsonl"))
                .filter(path -> { try { return Files.getLastModifiedTime(path).toMillis() < cutoff; } catch (IOException e) { return false; } })
                .forEach(path -> { try { Files.delete(path); } catch (IOException ignored) { WRITE_HEALTHY.set(false); } });
        }
    }
}
