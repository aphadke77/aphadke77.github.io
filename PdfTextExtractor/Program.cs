using System.Text;
using System.Text.Json;
using UglyToad.PdfPig;
using UglyToad.PdfPig.Content;

namespace PdfTextExtractor;

/// <summary>
/// Represents the extracted content of a single PDF page.
/// </summary>
public record PageContent(int PageNumber, string Text);

/// <summary>
/// Represents the full extraction result for one PDF file.
/// </summary>
public record PdfExtractionResult(
    string FileName,
    string FilePath,
    int TotalPages,
    PageContent[] Pages,
    string FullText
);

class Program
{
    static int Main(string[] args)
    {
        if (args.Length == 0)
        {
            PrintUsage();
            return 1;
        }

        // Collect PDF paths — accept individual files or directories.
        var pdfPaths = new List<string>();

        foreach (var arg in args)
        {
            if (Directory.Exists(arg))
            {
                pdfPaths.AddRange(
                    Directory.EnumerateFiles(arg, "*.pdf", SearchOption.AllDirectories));
            }
            else if (File.Exists(arg))
            {
                pdfPaths.Add(arg);
            }
            else
            {
                Console.Error.WriteLine($"Warning: '{arg}' is not a valid file or directory. Skipping.");
            }
        }

        if (pdfPaths.Count == 0)
        {
            Console.Error.WriteLine("Error: No PDF files found.");
            return 1;
        }

        Console.WriteLine($"Found {pdfPaths.Count} PDF file(s). Extracting text...");

        var results = new List<PdfExtractionResult>();
        int succeeded = 0, failed = 0;

        foreach (var path in pdfPaths)
        {
            try
            {
                var result = ExtractFromPdf(path);
                results.Add(result);
                Console.WriteLine($"  OK  {Path.GetFileName(path)} ({result.TotalPages} page(s))");
                succeeded++;
            }
            catch (Exception ex)
            {
                Console.Error.WriteLine($"  ERR {Path.GetFileName(path)}: {ex.Message}");
                failed++;
            }
        }

        // Write JSON output next to the first PDF, or current directory for a folder input.
        string outputDir = Directory.Exists(args[0])
            ? args[0]
            : Path.GetDirectoryName(Path.GetFullPath(args[0])) ?? ".";

        string outputPath = Path.Combine(outputDir, "extracted_text.json");

        var jsonOptions = new JsonSerializerOptions
        {
            WriteIndented = true,
            PropertyNamingPolicy = JsonNamingPolicy.CamelCase
        };

        File.WriteAllText(outputPath, JsonSerializer.Serialize(results, jsonOptions), Encoding.UTF8);

        Console.WriteLine();
        Console.WriteLine($"Done. {succeeded} succeeded, {failed} failed.");
        Console.WriteLine($"JSON written to: {outputPath}");

        return failed > 0 ? 2 : 0;
    }

    /// <summary>
    /// Opens a PDF, reads every page, and returns a structured result.
    /// </summary>
    private static PdfExtractionResult ExtractFromPdf(string filePath)
    {
        var pages = new List<PageContent>();
        var fullTextBuilder = new StringBuilder();

        using var document = PdfDocument.Open(filePath);

        foreach (Page page in document.GetPages())
        {
            // PdfPig concatenates words; joining with a space gives readable prose.
            string pageText = string.Join(" ", page.GetWords().Select(w => w.Text));
            pages.Add(new PageContent(page.Number, pageText));
            fullTextBuilder.AppendLine(pageText);
        }

        return new PdfExtractionResult(
            FileName: Path.GetFileName(filePath),
            FilePath: Path.GetFullPath(filePath),
            TotalPages: pages.Count,
            Pages: pages.ToArray(),
            FullText: fullTextBuilder.ToString().Trim()
        );
    }

    private static void PrintUsage()
    {
        Console.WriteLine("PDF Text Extractor — reads PDFs and writes extracted text to JSON.");
        Console.WriteLine();
        Console.WriteLine("Usage:");
        Console.WriteLine("  PdfTextExtractor <file.pdf> [file2.pdf ...]");
        Console.WriteLine("  PdfTextExtractor <directory>");
        Console.WriteLine();
        Console.WriteLine("Output:");
        Console.WriteLine("  extracted_text.json is written in the same directory as the input.");
        Console.WriteLine();
        Console.WriteLine("JSON schema:");
        Console.WriteLine("  [");
        Console.WriteLine("    {");
        Console.WriteLine("      \"fileName\":  \"report.pdf\",");
        Console.WriteLine("      \"filePath\":  \"/abs/path/report.pdf\",");
        Console.WriteLine("      \"totalPages\": 5,");
        Console.WriteLine("      \"pages\": [");
        Console.WriteLine("        { \"pageNumber\": 1, \"text\": \"...\" },");
        Console.WriteLine("        ...");
        Console.WriteLine("      ],");
        Console.WriteLine("      \"fullText\": \"all pages concatenated\"");
        Console.WriteLine("    }");
        Console.WriteLine("  ]");
    }
}
