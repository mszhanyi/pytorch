#pragma once

#include <chrono>
#include <map>
#include <string>

#include <c10/macros/Macros.h>
#include <torch/csrc/jit/frontend/source_ref.h>
#include <torch/csrc/jit/ir/ir.h>

namespace torch {
namespace jit {
namespace profiling {

struct Datapoint {
  using Timepoint = std::chrono::time_point<std::chrono::steady_clock>;
  SourceRange sourceRange;
  Timepoint start;
  Timepoint end;

  Datapoint(SourceRange sr)
      : sourceRange(std::move(sr)), start(std::chrono::steady_clock::now()) {}
};

class TORCH_API InstructionSpan {
 public:
  InstructionSpan(Node&);
  ~InstructionSpan();
  InstructionSpan(InstructionSpan&&) = delete;

 private:
  std::unique_ptr<Datapoint> datapoint_;
};

} // namespace profiling

struct TORCH_API InstructionStats {
  size_t count{0};
  std::chrono::nanoseconds duration{0};
};

/**
 * ScriptProfile is an underlying C++ implementation for TorchScript profiling.
 * The profiling section is specified by calling enable() and disable():
 *
 * ...
 * scriptProfile.enable();
 * ...
 * (scripts)
 * ...
 * scriptProfile.disable();
 * ...
 *
 * To retrieve collected runtime data, users may call dumpStats() and do
 * arbitrary filtering on the data they want. Note that dumpStats() should
 * not be called inside a profiling section.
 * In general, stats are aggregated per source function body, and then by line
 * number.
 */
class TORCH_API ScriptProfile {
  // Aggregates datapoints by function source id, then by line number.
  using LineMap = std::map<size_t, InstructionStats>;
  using Stats = std::map<SourceRef, LineMap, std::less<>>;

 public:
  void enable();
  void disable();
  const Stats& dumpStats();
  void addDatapoint(std::shared_ptr<profiling::Datapoint>);
  ~ScriptProfile();

 private:
  bool enabled_{false};
  std::vector<std::shared_ptr<profiling::Datapoint>> datapoints_;
  Stats stats_;
};

} // namespace jit
} // namespace torch