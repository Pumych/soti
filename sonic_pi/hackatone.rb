##| NOTE: The code below uses Sonic-Pi built-in synthesizers.
##|       For a more "orchestral" sound, use the 'Sonatina Orchestra' sample pack together with Robin Newman's loader:
##|       https://gist.github.com/rbnpi/992bcbdec785597453bf
##|       and follow instructions under "---Orchestra Mode---" tagged comments.


##| ---Orchestra Mode--- in Robin Newman's loader, insert the following changes:
##| 1. Delete lines 181-265
##| 2. Set the path in line 10 to your Sonatina sample pack location.
##| 3. Reduce sleep time in line 75 to 0.1
##| 4. Insert the following code after line 68:
##|    ##| Get instrument ranges and set them into a global variable:
##|    insts = {}
##|    voices.each do |v|
##|      lo = note v[4] - 2
##|      hi = note v[5] + 4
##|      insts[v[0]] = [lo, hi]
##|    end
##|    set :instruments, insts

##| Loading external 'Sonatina orchestra' sample pack loader:
##| ---Orchestra Mode--- uncomment next line
##| run_file "/<path>/sonatina_loader.rb"

##| ---Orchestra Mode--- uncomment next line
##| sleep 3  # Leaving the 'sonatina_loader.rb' some extra time to make sure it is loaded properly.

##| Global parameters:
##| ---Orchestra Mode--- uncomment next line
##| instruments = get(:instruments)                        # Collects range data for all the "Sonatina" sample pack instruments.

##| ---Orchestra Mode--- replace next line with: base_scale  = scale(:c0, :minor, num_octaves: 9).to_a
base_scale  = scale(:c2, :minor, num_octaves: 7).to_a  # Defines the scale that will be played. Choose your favorite one :)
insts = synth_names.shuffle


global_volume       = 1       # Used for globally setting the sonified traffic volume down / up.
note_ommitting_rate = 3       # One out of 'note_ommitting_rate' notes will be ommitted, just to make it sound not too robotic.
min_note_duration   = 0.1     # Duration is a randomized a bit, to make the sound less robotic.
max_note_duration   = 0.7

##| Traffic input OSC messages
note_osc_message      = "/osc/note"
amp_osc_message       = "/osc/amp"

##| Panic button OSC messages
mitigation_osc_message = "/osc/2/buttonListener"
back_osc_message      = "/osc/1/buttonListener"

##| Sound samples for panic buttons
mitigation_sample      = "/<path>/<ddos_mitigation_soundfile>.wav"
back_sample           = "/<path>/<mitigation_finished_soundfile>.wav"

##| ---Orchestra Mode--- uncomment next paragraph
##| ##| Choose your favorite instruments. Pick them from the sonatina_loader.rb file.
##| insts= ["Violas sus", "1st Violins sus", "Horn", "Harp", "Timpani p lh",
##|         "Xylophone", "Violas piz", "Bassoon", "Chorus female", "Tenor Trombone",
##|         "Flute", "Chorus male", "Basses piz", "Tuba stc"]


##| Transform a value between 0 and 100 into a note within base_scale.
##| Amplify high values.
define :value_to_note do |_note, _amp|
  # Set a note on the scale. If value is 0, ommit the note.
  if (_note != 0)
    note_index = (_note * (base_scale.length - 1) / 100).to_i
    nt = base_scale[note_index]
  else
    nt = nil
  end
  
##| ---Orchestra Mode--- replace the above paragraph with:
##| define :value_to_note do |_note, _amp, scale_input|
##|   # Set a note on the scale. If value is 0, ommit the note.
##|   if (_note != 0)
##|     note_index = (_note * (scale_input.length - 1) / 100).to_i
##|     nt = scale_input[note_index]
##|   else
##|     nt = nil
##|   end
  
  # Volume modification: Amplify high values, attenuate low values.
  if (_note > 80)
    velocity = global_volume * _amp * (_note * 3 / 100.0)
  else
    velocity = global_volume * _amp * (_note * 0.2)
  end
  
  # Duration is a randomized a bit, to make the sound less robotic.
  duration  = rrand(min_note_duration, max_note_duration)
  
  return {'note' => nt, 'velocity' => velocity, 'duration' => duration}
end


##| Trim a given base scale to a given range.
##| ('instrument range' should be a list of this format: [lowest_note, highest_note])
define :trim_scale do |base_scale, instrument_range|
  output = []
  lowest_note  = instrument_range[0]
  highest_note = instrument_range[1]
  
  base_scale.each do |n|
    if ((n >= lowest_note) and (n <= highest_note))
      output.push(n)
    end
  end
  
  return output
end

##| ---Orchestra Mode--- uncomment next paragraph
##| ##| Setting 'instrument_scales' to be a dictionary where the key is the instrument name
##| ##| and the value is the part of the base scale that meets the instrument's range limitations:
##| instrument_scales = {}
##| instruments.each do |inst_k, inst_v|
##|   trimmed_scale = trim_scale(base_scale, inst_v)
##|   instrument_scales[inst_k] = trimmed_scale
##| end

##| ---Orchestra Mode--- comment out next function definition
define :pl do |tone, duration, instrument, velocity|
  synth instrument, note: tone, sustain: duration, amp: velocity
end

##| Sonification main loop:
with_fx :reverb do
  live_loop :sonify_traffic do
    use_real_time
    
    play_note = sync note_osc_message
    play_amp  = sync amp_osc_message
    
    # Loop over the instruments. Each will be matched to its corresponding element in the input /osc/note and /osc/amp arrays.
    for i in 0..[insts.length - 1, play_note.length - 1].min
      # One out of 'note_ommitting_rate' notes will be ommitted, just to make it sound not too robotic.
      ommit_note = one_in(note_ommitting_rate) ? false : true
      
      if (not ommit_note)
        instrument = insts[i]
        ##| ---Orchestra Mode--- replace next line with: note_params = value_to_note(play_note[i], play_amp[i], instrument_scales[instrument])
        note_params = value_to_note(play_note[i], play_amp[i])
        tone     = note note_params['note']
        velocity = note_params['velocity']
        duration = note_params['duration']
        
        # 'tone' will get 'nil' when the traffic rate is 0. In such case, no note will be played
        if (tone != nil)
          ##| ---Orchestra Mode--- replace next line with: pl(tone, duration, instrument, 0, 0, velocity)
          pl(tone, duration, instrument, velocity)
        end
        
      end
    end
    
  end
end


##| Panic button loops:
live_loop :mitigation_pushbutton do
  use_real_time
  sync mitigation_osc_message
  sample mitigation_sample, amp: 5
  global_volume = 0.05
  sleep 6
  global_volume = 0.3
end


live_loop :back_to_business_pushbutton do
  use_real_time
  sync back_osc_message
  sample back_sample, amp: 3
  global_volume = 0.05
  sleep 4
  global_volume = 1
end


