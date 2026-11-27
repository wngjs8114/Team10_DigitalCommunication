#include "Modulation/QAMa/QAM32.h"

#include <algorithm>
#include <array>
#include <charconv>
#include <cmath>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <numeric>
#include <random>
#include <sstream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <vector>

namespace {

constexpr int BITS = 5;
constexpr int POINTS = 1 << BITS;
constexpr int MAX_EBN0_DB = 20;
constexpr std::uint32_t BASE_SEED = 20261128;
constexpr int DEFAULT_MAX_SYMBOLS = 2000000;
constexpr int DEFAULT_TARGET_ERRORS = 2000;
constexpr auto MAX_SEED = std::numeric_limits<std::uint32_t>::max() - MAX_EBN0_DB;
constexpr std::array<std::string_view, 4> SCHEMES{"Rectangular", "Type1", "Type2", "Type3"};
using Labels = std::array<int, POINTS>;
using Seen = std::array<bool, POINTS>;

template <class Integer>
Integer parse_integer(std::string_view text, Integer minimum, Integer maximum, const char* name)
{
    Integer value = 0;
    const auto end = text.data() + text.size();
    const auto parsed = std::from_chars(text.data(), end, value);
    if (parsed.ec != std::errc{} || parsed.ptr != end || value < minimum || value > maximum) {
        throw std::invalid_argument(std::string("Invalid ") + name);
    }
    return value;
}

float parse_coordinate(const std::string& field)
{
    std::size_t consumed = 0;
    const float value = std::stof(field, &consumed);
    if (consumed != field.size() || !std::isfinite(value)) {
        throw std::invalid_argument("Invalid normalized coordinate");
    }
    return value;
}

struct Constellation {
    float coordinates[POINTS][2]{};
    Labels optimized{};
    Seen ids{};
    Seen labels{};
    int size = 0;
};

std::array<Constellation, SCHEMES.size()> read_mapped_csv(const std::filesystem::path& path)
{
    std::ifstream input(path);
    std::string line;
    const auto read_line = [&] {
        if (!std::getline(input, line)) {
            return false;
        }
        if (!line.empty() && line.back() == '\r') {
            line.pop_back();
        }
        return true;
    };

    if (!read_line() || line != "scheme,point_id,I_raw,Q_raw,I_norm,Q_norm,bit_label") {
        throw std::runtime_error("Cannot read mapped constellation CSV header");
    }
    std::array<Constellation, SCHEMES.size()> constellations{};
    int line_number = 1;
    while (read_line()) {
        ++line_number;
        try {
            std::istringstream row(line);
            std::array<std::string, 7> fields;
            for (auto& field : fields) {
                if (!std::getline(row, field, ',') || field.empty()) {
                    throw std::runtime_error("Expected seven nonempty CSV fields");
                }
            }
            if (!row.eof()) {
                throw std::runtime_error("Unexpected mapped CSV columns");
            }
            const auto scheme = std::find(SCHEMES.begin(), SCHEMES.end(), fields[0]);
            if (scheme == SCHEMES.end()) {
                throw std::runtime_error("Unknown scheme");
            }
            auto& constellation = constellations[scheme - SCHEMES.begin()];
            const int id = parse_integer(fields[1], 0, POINTS - 1, "point_id");
            const std::string& bits = fields[6];
            if (bits.size() != BITS || bits.find_first_not_of("01") != std::string::npos) {
                throw std::runtime_error("bit_label must have exactly five binary digits");
            }
            const int label = std::stoi(bits, nullptr, 2);
            if (constellation.ids[id] || constellation.labels[label]) {
                throw std::runtime_error("Duplicate point_id or bit_label");
            }
            // The Python validator checks raw coordinates and the normalization.
            // The modem uses the supplied normalized coordinates directly.
            constellation.coordinates[id][0] = parse_coordinate(fields[4]);
            constellation.coordinates[id][1] = parse_coordinate(fields[5]);
            constellation.optimized[id] = label;
            constellation.ids[id] = constellation.labels[label] = true;
            ++constellation.size;
        } catch (const std::exception& error) {
            throw std::runtime_error("Mapped CSV line " + std::to_string(line_number) + ": " + error.what());
        }
    }
    if (input.bad() || std::any_of(constellations.begin(), constellations.end(),
                                  [](const Constellation& scheme) { return scheme.size != POINTS; })) {
        throw std::runtime_error("Expected 32 mapped points for each of four schemes");
    }
    return constellations;
}

std::vector<int> parse_levels(std::string_view text)
{
    std::vector<int> levels;
    do {
        const auto comma = text.find(',');
        const int level = parse_integer(text.substr(0, comma), 0, MAX_EBN0_DB, "Eb/N0 level");
        if (!levels.empty() && level <= levels.back()) {
            throw std::invalid_argument("Eb/N0 levels must be strictly increasing");
        }
        levels.push_back(level);
        if (comma == std::string_view::npos) {
            break;
        }
        text.remove_prefix(comma + 1);
    } while (true);
    return levels;
}

class CsvQam32 : public QAMa {
public:
    explicit CsvQam32(Constellation& constellation)
    {
        bitPerSymbol = BITS;
        AssignConstellation(constellation.coordinates);
    }
};

template <class Modem>
class Experiment : public Modem {
public:
    using Modem::Modem;

    double validate_energy()
    {
        double sum = 0.0;
        for (int id = 0; id < POINTS; ++id) {
            const Complex point = this->Modulation(id);
            sum += double(point.i) * point.i + double(point.q) * point.q;
            if (this->Demodulation(point) != id) {
                throw std::runtime_error("Noiseless modulation/demodulation mismatch");
            }
        }
        const double energy = sum / POINTS;
        if (!std::isfinite(energy) || std::abs(energy - 1.0) > 1e-6) {
            throw std::runtime_error("Expected normalized Es = 1");
        }
        return energy;
    }

    static double noise_variance(int ebn0_db)
    {
        // Es = 1, Es/N0 = k * Eb/N0, and each real axis has variance N0/2.
        return 1.0 / (2.0 * BITS * std::pow(10.0, ebn0_db / 10.0));
    }

    void run_point(std::ostream& csv, std::string_view scheme, int ebn0_db,
                   int max_symbols, int target_errors, std::uint32_t base_seed,
                   const Labels* optimized)
    {
        this->numSymbol = this->numSymbolError = this->numBitError = 0;
        const std::uint32_t seed = base_seed + ebn0_db;
        std::mt19937 random(seed);
        std::uniform_int_distribution<int> point_id(0, POINTS - 1);
        std::normal_distribution<double> noise(0.0, std::sqrt(noise_variance(ebn0_db)));
        int optimized_bit_errors = 0;

        // Decode once. Both mappings see the same transmitted/decided point IDs.
        while (this->numSymbol < max_symbols && this->numSymbolError < target_errors) {
            const int source = point_id(random);
            const Complex tx = this->Modulation(source);
            const double noise_i = noise(random);
            const double noise_q = noise(random);
            const Complex rx(static_cast<float>(tx.i + noise_i),
                             static_cast<float>(tx.q + noise_q));
            const int decision = this->Demodulation(rx);
            this->ErrorCount(source, decision);
            if (optimized && source != decision) {
                const int different = (*optimized)[source] ^ (*optimized)[decision];
                for (int bit = 0; bit < BITS; ++bit) {
                    optimized_bit_errors += (different >> bit) & 1;
                }
            }
        }

        const int num_bits = BITS * this->numSymbol;
        const double ser = double(this->numSymbolError) / this->numSymbol;
        const auto write_row = [&](std::string_view mapping, int bit_errors) {
            csv << scheme << ',' << mapping << ',' << ebn0_db << ',' << this->numSymbol << ','
                << num_bits << ',' << this->numSymbolError << ',' << bit_errors << ','
                << ser << ',' << double(bit_errors) / num_bits << ',' << seed << '\n';
        };
        write_row("initial", this->numBitError);
        if (optimized) {
            write_row("optimized", optimized_bit_errors);
        }
    }
};

}  // namespace

int main(int argc, char** argv)
{
    try {
        const bool paired = argc >= 2 && std::string_view(argv[1]) == "--mapped-csv";
        if ((!paired && (argc < 2 || argc > 4)) || (paired && argc != 8)) {
            std::cerr << "Usage: rectangular_experiment OUTPUT_CSV [MAX_SYMBOLS] [TARGET_SYMBOL_ERRORS]\n"
                      << "   or: rectangular_experiment --mapped-csv INPUT_CSV OUTPUT_CSV LEVELS "
                         "MAX_SYMBOLS TARGET_SYMBOL_ERRORS BASE_SEED\n";
            return 2;
        }
        const int max_int = std::numeric_limits<int>::max();
        const int max_argument = paired ? 5 : 2;
        const int target_argument = max_argument + 1;
        const int max_symbols = argc > max_argument
            ? parse_integer(argv[max_argument], 1, max_int / BITS, "MAX_SYMBOLS")
            : DEFAULT_MAX_SYMBOLS;
        const int target_errors = argc > target_argument
            ? parse_integer(argv[target_argument], 1, max_int, "TARGET_SYMBOL_ERRORS")
            : DEFAULT_TARGET_ERRORS;
        const auto base_seed = paired
            ? parse_integer(argv[7], std::uint32_t{0}, MAX_SEED, "BASE_SEED") : BASE_SEED;

        std::vector<int> levels(MAX_EBN0_DB + 1);
        std::iota(levels.begin(), levels.end(), 0);
        const std::filesystem::path output(paired ? argv[3] : argv[1]);
        std::array<Constellation, SCHEMES.size()> constellations{};
        if (paired) {
            levels = parse_levels(argv[4]);
            const std::filesystem::path input(argv[2]);
            if (std::filesystem::weakly_canonical(input) == std::filesystem::weakly_canonical(output)) {
                throw std::invalid_argument("Input and output paths must differ");
            }
            constellations = read_mapped_csv(input);
            for (auto& constellation : constellations) {
                Experiment<CsvQam32>(constellation).validate_energy();
            }
        }
        const double variance_at_zero = Experiment<QAM32>::noise_variance(0);
        if (std::abs(variance_at_zero - 0.1) > 1e-12) {
            throw std::runtime_error("Unexpected 0 dB axis noise variance");
        }

        if (output.has_parent_path()) {
            std::filesystem::create_directories(output.parent_path());
        }
        std::ofstream csv(output, std::ios::binary);
        csv.exceptions(std::ios::badbit | std::ios::failbit);
        csv << "scheme,mapping,ebn0_db,num_symbols,num_bits,symbol_errors,bit_errors,SER,BER,seed\n"
            << std::setprecision(std::numeric_limits<double>::max_digits10);
        if (paired) {
            for (std::size_t i = 0; i < SCHEMES.size(); ++i) {
                Experiment<CsvQam32> experiment(constellations[i]);
                for (const int level : levels) {
                    experiment.run_point(csv, SCHEMES[i], level, max_symbols, target_errors,
                                         base_seed, &constellations[i].optimized);
                }
            }
            std::cout << "Validated 32 normalized points per scheme; 0 dB axis variance = "
                      << variance_at_zero << '\n';
        } else {
            Experiment<QAM32> experiment(0);
            std::cout << std::defaultfloat << std::setprecision(10)
                      << "Es = " << experiment.validate_energy()
                      << ", axis noise variance at Eb/N0 = 0 dB: " << variance_at_zero << '\n';
            for (const int level : levels) {
                experiment.run_point(csv, "Rectangular", level, max_symbols, target_errors,
                                     base_seed, nullptr);
            }
        }
        csv.close();
        std::cout << "Wrote " << output << '\n';
    } catch (const std::exception& error) {
        std::cerr << "Experiment failed: " << error.what() << '\n';
        return 1;
    }
}
