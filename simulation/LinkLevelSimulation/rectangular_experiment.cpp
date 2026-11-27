#include "Modulation/QAMa/QAM32.h"

#include <charconv>
#include <cstdint>
#include <filesystem>
#include <iomanip>
#include <limits>
#include <random>
#include <stdexcept>
#include <string_view>

namespace {

constexpr int MAX_EBN0_DB = 20;
constexpr std::uint32_t BASE_SEED = 20261128;
constexpr int DEFAULT_MAX_SYMBOLS = 2000000;
constexpr int DEFAULT_TARGET_ERRORS = 2000;

int positive_integer(std::string_view text, int maximum, const char* name)
{
    int value = 0;
    const auto end = text.data() + text.size();
    const auto parsed = std::from_chars(text.data(), end, value);
    if (parsed.ec != std::errc{} || parsed.ptr != end || value < 1 || value > maximum) {
        throw std::invalid_argument(std::string("Invalid ") + name);
    }
    return value;
}

class RectangularExperiment : public QAM32 {
public:
    RectangularExperiment() : QAM32(0) {}

    double average_symbol_energy()
    {
        const int count = 1 << BitPerSymbol();
        double sum = 0.0;
        for (int label = 0; label < count; ++label) {
            const Complex point = Modulation(label);
            sum += double(point.i) * point.i + double(point.q) * point.q;
            if (Demodulation(point) != label) {
                throw std::runtime_error("Noiseless modulation/demodulation mismatch");
            }
        }
        return sum / count;
    }

    double noise_variance(int ebn0_db)
    {
        // Es = 1, Es/N0 = k * Eb/N0, and each real axis has variance N0/2.
        return 1.0 / (2.0 * BitPerSymbol() * std::pow(10.0, ebn0_db / 10.0));
    }

    void run_point(std::ostream& csv, int ebn0_db, int max_symbols, int target_errors)
    {
        numSymbol = numSymbolError = numBitError = 0;
        const std::uint32_t seed = BASE_SEED + ebn0_db;
        std::mt19937 random(seed);
        std::uniform_int_distribution<int> label(0, (1 << BitPerSymbol()) - 1);
        std::normal_distribution<double> noise(0.0, std::sqrt(noise_variance(ebn0_db)));

        while (numSymbol < max_symbols && numSymbolError < target_errors) {
            const int source = label(random);
            const Complex tx = Modulation(source);
            const double noise_i = noise(random);
            const double noise_q = noise(random);
            const Complex rx(static_cast<float>(tx.i + noise_i),
                             static_cast<float>(tx.q + noise_q));
            ErrorCount(source, Demodulation(rx));
        }

        const int num_bits = BitPerSymbol() * numSymbol;
        const double ser = double(numSymbolError) / numSymbol;
        const double ber = double(numBitError) / num_bits;
        csv << "Rectangular,initial," << ebn0_db << ',' << numSymbol << ','
            << num_bits << ',' << numSymbolError << ',' << numBitError << ','
            << ser << ',' << ber << ',' << seed << '\n';
    }
};

}  // namespace

int main(int argc, char** argv)
{
    try {
        if (argc < 2 || argc > 4) {
            std::cerr << "Usage: rectangular_experiment OUTPUT_CSV [MAX_SYMBOLS] [TARGET_SYMBOL_ERRORS]\n";
            return 2;
        }
        // The original error counters are int. Bound both the bit count and bit errors.
        const int max_int = std::numeric_limits<int>::max();
        const int max_symbols = argc >= 3 ? positive_integer(argv[2], max_int / 5, "MAX_SYMBOLS")
                                          : DEFAULT_MAX_SYMBOLS;
        const int target_errors = argc >= 4 ? positive_integer(argv[3], max_int, "TARGET_SYMBOL_ERRORS")
                                            : DEFAULT_TARGET_ERRORS;

        RectangularExperiment experiment;
        const double energy = experiment.average_symbol_energy();
        const double variance_at_zero = experiment.noise_variance(0);
        if (std::abs(energy - 1.0) > 1e-6 || std::abs(variance_at_zero - 0.1) > 1e-12) {
            throw std::runtime_error("Unexpected Es or 0 dB axis noise variance");
        }
        std::cout << std::defaultfloat << std::setprecision(10)
                  << "Es = " << energy << ", axis noise variance at Eb/N0 = 0 dB: "
                  << variance_at_zero << '\n';

        const std::filesystem::path output(argv[1]);
        if (output.has_parent_path()) {
            std::filesystem::create_directories(output.parent_path());
        }
        std::ofstream csv(output, std::ios::binary);
        csv.exceptions(std::ios::badbit | std::ios::failbit);
        csv << "scheme,mapping,ebn0_db,num_symbols,num_bits,symbol_errors,bit_errors,SER,BER,seed\n"
            << std::setprecision(std::numeric_limits<double>::max_digits10);
        for (int ebn0_db = 0; ebn0_db <= MAX_EBN0_DB; ++ebn0_db) {
            experiment.run_point(csv, ebn0_db, max_symbols, target_errors);
        }
        csv.close();
        std::cout << "Wrote " << output << '\n';
    } catch (const std::exception& error) {
        std::cerr << "Experiment failed: " << error.what() << '\n';
        return 1;
    }
}
