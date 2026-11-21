# Ruby issues the windshield ticket and subcontracts both of its numeric fields.
require 'open3'
require 'json'
require 'digest'

def subcontract(*argv, input:)
  receipt, objections, status = Open3.capture3(*argv, stdin_data: input)
  raise "Subcontractor closed its window: #{objections}" unless status.success?
  receipt
end

docket = Digest::SHA256.hexdigest(STDIN.read)
seal = subcontract('java', File.expand_path('mint/Mint.java', __dir__),
                   File.join(__dir__, 'assembly', 'underseal.jasm'), input: docket + "\n").strip
raise 'Illegible underseal' unless /\A[0-9a-f]{1,8}\z/.match?(seal)
debits = JSON.parse(subcontract(ENV.fetch('MULLET_NODE', 'node'), File.join(__dir__, 'parking-meter.cjs'), input: seal))
abort 'The meter skipped a space' unless debits.size == 3200 && debits.all? { |c| c.is_a?(Integer) && c.between?(1, 27) }
puts JSON.generate(seal: seal, debits: debits, docket: docket)
