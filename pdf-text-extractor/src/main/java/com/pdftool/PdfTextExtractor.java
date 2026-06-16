package com.pdftool;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import org.apache.pdfbox.Loader;
import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.pdmodel.PDDocumentInformation;
import org.apache.pdfbox.text.PDFTextStripper;

import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * PDF Text Extractor
 *
 * Extracts text from one or more PDF files and writes the results to a JSON file.
 *
 * Usage:
 *   java -jar pdf-text-extractor-1.0.0.jar <input.pdf> [output.json]
 *   java -jar pdf-text-extractor-1.0.0.jar <pdf-directory> [output.json]
 *
 * If output path is omitted, output is written to "output.json" in the current directory.
 */
public class PdfTextExtractor {

    public static void main(String[] args) {
        if (args.length == 0) {
            printUsage();
            System.exit(1);
        }

        String inputPath  = args[0];
        String outputPath = args.length >= 2 ? args[1] : "output.json";

        File input = new File(inputPath);
        if (!input.exists()) {
            System.err.println("ERROR: Input path does not exist: " + inputPath);
            System.exit(1);
        }

        List<File> pdfFiles = collectPdfFiles(input);
        if (pdfFiles.isEmpty()) {
            System.err.println("ERROR: No PDF files found at: " + inputPath);
            System.exit(1);
        }

        System.out.println("Found " + pdfFiles.size() + " PDF file(s) to process.");

        List<Map<String, Object>> results = new ArrayList<>();
        int success = 0, failure = 0;

        for (File pdf : pdfFiles) {
            System.out.print("Processing: " + pdf.getName() + " ... ");
            Map<String, Object> record = extractFromPdf(pdf);
            results.add(record);
            if (Boolean.TRUE.equals(record.get("success"))) {
                System.out.println("OK");
                success++;
            } else {
                System.out.println("FAILED (" + record.get("error") + ")");
                failure++;
            }
        }

        // Build top-level JSON envelope
        Map<String, Object> envelope = new HashMap<>();
        envelope.put("extractedAt", LocalDateTime.now()
                .format(DateTimeFormatter.ISO_LOCAL_DATE_TIME));
        envelope.put("totalFiles",    pdfFiles.size());
        envelope.put("successCount",  success);
        envelope.put("failureCount",  failure);
        envelope.put("documents",     results);

        writeJson(envelope, outputPath);

        System.out.println("\nDone. Results written to: " + outputPath);
        System.out.println("  Success: " + success + "  |  Failed: " + failure);
    }

    // -----------------------------------------------------------------------
    // PDF extraction
    // -----------------------------------------------------------------------

    private static Map<String, Object> extractFromPdf(File pdf) {
        Map<String, Object> record = new HashMap<>();
        record.put("fileName",  pdf.getName());
        record.put("filePath",  pdf.getAbsolutePath());
        record.put("fileSizeBytes", pdf.length());

        try (PDDocument doc = Loader.loadPDF(pdf)) {

            // Metadata
            PDDocumentInformation info = doc.getDocumentInformation();
            Map<String, String> metadata = new HashMap<>();
            metadata.put("title",    nullSafe(info.getTitle()));
            metadata.put("author",   nullSafe(info.getAuthor()));
            metadata.put("subject",  nullSafe(info.getSubject()));
            metadata.put("keywords", nullSafe(info.getKeywords()));
            metadata.put("creator",  nullSafe(info.getCreator()));
            metadata.put("producer", nullSafe(info.getProducer()));
            if (info.getCreationDate() != null) {
                metadata.put("creationDate",
                        info.getCreationDate().getTime().toString());
            }
            if (info.getModificationDate() != null) {
                metadata.put("modificationDate",
                        info.getModificationDate().getTime().toString());
            }

            int pageCount = doc.getNumberOfPages();
            record.put("pageCount", pageCount);
            record.put("metadata",  metadata);

            // Per-page text extraction
            PDFTextStripper stripper = new PDFTextStripper();
            List<Map<String, Object>> pages = new ArrayList<>();

            for (int i = 1; i <= pageCount; i++) {
                stripper.setStartPage(i);
                stripper.setEndPage(i);
                String pageText = stripper.getText(doc).trim();

                Map<String, Object> pageRecord = new HashMap<>();
                pageRecord.put("pageNumber",   i);
                pageRecord.put("charCount",    pageText.length());
                pageRecord.put("wordCount",    countWords(pageText));
                pageRecord.put("text",         pageText);
                pages.add(pageRecord);
            }

            record.put("pages",   pages);
            record.put("success", true);

        } catch (IOException e) {
            record.put("success", false);
            record.put("error",   e.getMessage());
        }

        return record;
    }

    // -----------------------------------------------------------------------
    // Helpers
    // -----------------------------------------------------------------------

    /** Recursively collects all .pdf files from a file or directory. */
    private static List<File> collectPdfFiles(File input) {
        List<File> list = new ArrayList<>();
        if (input.isFile() && input.getName().toLowerCase().endsWith(".pdf")) {
            list.add(input);
        } else if (input.isDirectory()) {
            try {
                Files.walk(Paths.get(input.toURI()))
                        .map(Path::toFile)
                        .filter(f -> f.isFile() && f.getName().toLowerCase().endsWith(".pdf"))
                        .forEach(list::add);
            } catch (IOException e) {
                System.err.println("WARNING: Could not walk directory: " + e.getMessage());
            }
        }
        return list;
    }

    private static void writeJson(Object data, String outputPath) {
        Gson gson = new GsonBuilder().setPrettyPrinting().disableHtmlEscaping().create();
        File outFile = new File(outputPath);
        // Create parent directories if needed
        if (outFile.getParentFile() != null) {
            outFile.getParentFile().mkdirs();
        }
        try (FileWriter writer = new FileWriter(outFile)) {
            gson.toJson(data, writer);
        } catch (IOException e) {
            System.err.println("ERROR: Could not write JSON output: " + e.getMessage());
            System.exit(1);
        }
    }

    private static String nullSafe(String value) {
        return value != null ? value : "";
    }

    private static int countWords(String text) {
        if (text == null || text.isBlank()) return 0;
        return text.trim().split("\\s+").length;
    }

    private static void printUsage() {
        System.out.println("PDF Text Extractor v1.0.0");
        System.out.println("=========================");
        System.out.println("Extracts text from PDF files and saves results to JSON.\n");
        System.out.println("Usage:");
        System.out.println("  java -jar pdf-text-extractor-1.0.0.jar <input.pdf> [output.json]");
        System.out.println("  java -jar pdf-text-extractor-1.0.0.jar <pdf-directory> [output.json]");
        System.out.println();
        System.out.println("Arguments:");
        System.out.println("  <input.pdf|pdf-directory>  Path to a single PDF or a folder of PDFs");
        System.out.println("  [output.json]              Output JSON file path (default: output.json)");
        System.out.println();
        System.out.println("Examples:");
        System.out.println("  java -jar pdf-text-extractor-1.0.0.jar report.pdf");
        System.out.println("  java -jar pdf-text-extractor-1.0.0.jar report.pdf results.json");
        System.out.println("  java -jar pdf-text-extractor-1.0.0.jar ./pdfs/ all-results.json");
    }
}
